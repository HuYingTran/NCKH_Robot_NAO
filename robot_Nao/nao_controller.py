# -*- coding: utf-8 -*-
"""
nao_controller.py
Thin wrapper around the NAOqi SDK that drives the NAO humanoid robot to
follow a path produced by the GA + A* planner.

If the NAOqi SDK is not installed (very common on Python 3 / Windows),
the controller transparently falls back to a *fake* mode that prints
each action to the console — useful for development and demos.

API:
    ctrl = NaoController(cell_size_m=0.10, walk_speed=0.5)
    ok, msg = ctrl.connect(ip="192.168.1.10", port=9559)
    ctrl.stand_init()
    ctrl.say("Bắt đầu giao hàng")
    ctrl.follow_path_cells(path, on_progress=lambda i, n: ...)
    ctrl.disconnect()
"""
from __future__ import annotations

import math
from typing import Callable, List, Optional, Tuple

Point = Tuple[int, int]


class NaoController:
    def __init__(self,
                 cell_size_m: float = 0.10,
                 walk_speed: float = 0.5,
                 fake: bool = False):
        """
        cell_size_m : real-world width of one grid cell in meters
                      (default 0.10 m → 100 × 100 grid = 10 m × 10 m room).
        walk_speed  : passed to ALMotion.setWalkArmsEnabled etc. (0..1)
        fake        : force fake mode even if SDK is installed.
        """
        self.cell_size_m = float(cell_size_m)
        self.walk_speed = float(walk_speed)
        self.fake = bool(fake)
        self.connected = False
        self._sdk_name = None       # "qi", "naoqi" or "fake"
        self.session = None
        self.motion = None
        self.posture = None
        self.tts = None
        # internal heading (rad), 0 = +x, ccw positive
        self._theta = 0.0

    # ------------------------------------------------------------- connect
    def connect(self, ip: str = "127.0.0.1", port: int = 9559
                ) -> Tuple[bool, str]:
        """Try qi-framework first, then legacy naoqi, otherwise fake mode."""
        if self.fake:
            self.connected = True
            self._sdk_name = "fake"
            return True, "FAKE mode (NAOqi not used)."
        # Try qi-framework (Python 3)
        try:
            import qi  # type: ignore
            session = qi.Session()
            session.connect(f"tcp://{ip}:{port}")
            self.session = session
            self.motion = session.service("ALMotion")
            self.posture = session.service("ALRobotPosture")
            self.tts = session.service("ALTextToSpeech")
            self._sdk_name = "qi"
            self.connected = True
            return True, f"Connected via qi-framework to {ip}:{port}"
        except Exception as e_qi:
            err_qi = str(e_qi)
        # Try legacy naoqi (Python 2)
        try:
            from naoqi import ALProxy  # type: ignore
            self.motion = ALProxy("ALMotion", ip, port)
            self.posture = ALProxy("ALRobotPosture", ip, port)
            self.tts = ALProxy("ALTextToSpeech", ip, port)
            self._sdk_name = "naoqi"
            self.connected = True
            return True, f"Connected via legacy NAOqi to {ip}:{port}"
        except Exception as e_old:
            err_old = str(e_old)
        # Both failed → fake mode
        self.fake = True
        self.connected = True
        self._sdk_name = "fake"
        return True, ("NAOqi SDK not available — running in FAKE mode.\n"
                      f"  qi error  : {err_qi}\n"
                      f"  naoqi err : {err_old}")

    def disconnect(self):
        if not self.connected:
            return
        if self._sdk_name == "qi" and self.session is not None:
            try:
                self.session.close()
            except Exception:
                pass
        self.connected = False
        self.motion = self.posture = self.tts = self.session = None

    # --------------------------------------------------------- high-level
    def stand_init(self):
        if not self.connected:
            return
        if self._sdk_name == "fake":
            print("[FAKE NAO] goToPosture(StandInit)")
            return
        try:
            self.posture.goToPosture("StandInit", 0.6)
        except Exception as e:
            print(f"[NAO] stand_init failed: {e}")

    def rest(self):
        if not self.connected:
            return
        if self._sdk_name == "fake":
            print("[FAKE NAO] goToPosture(Crouch) + rest")
            return
        try:
            self.posture.goToPosture("Crouch", 0.6)
            self.motion.rest()
        except Exception as e:
            print(f"[NAO] rest failed: {e}")

    def say(self, text: str):
        if not self.connected:
            return
        if self._sdk_name == "fake":
            print(f"[FAKE NAO] say: {text}")
            return
        try:
            self.tts.say(text)
        except Exception as e:
            print(f"[NAO] say failed: {e}")

    def move_to(self, dx_m: float, dy_m: float, dtheta_rad: float = 0.0):
        """Robot-frame moveTo (dx forward, dy left, dtheta yaw)."""
        if not self.connected:
            return
        if self._sdk_name == "fake":
            print(f"[FAKE NAO] moveTo dx={dx_m:+.3f} m  dy={dy_m:+.3f} m  "
                  f"dθ={math.degrees(dtheta_rad):+.1f}°")
            return
        try:
            self.motion.moveTo(float(dx_m), float(dy_m), float(dtheta_rad))
        except Exception as e:
            print(f"[NAO] moveTo failed: {e}")

    # ----------------------------------------------------- follow a path
    def follow_path_cells(self,
                          path: List[Point],
                          on_progress: Optional[Callable[[int, int], None]] = None,
                          stop_flag: Optional[Callable[[], bool]] = None):
        """
        Walk along a sequence of grid cells.

        Strategy (kept simple and human-readable):
          for each consecutive pair of cells (p, q) along the path
            heading = atan2(q.y - p.y, q.x - p.x)            # world frame
            dtheta  = heading - current_heading              # rotate first
            moveTo(0, 0, dtheta)
            dist = ||q - p|| * cell_size_m
            moveTo(dist, 0, 0)                               # then walk
            current_heading = heading

        World convention used:
          • +x = grid X axis (right)
          • +y = grid Y axis (down on screen, but it's just another axis)
          • Robot heading 0 = facing +x.
        """
        if not self.connected or not path or len(path) < 2:
            return
        for i in range(1, len(path)):
            if stop_flag and stop_flag():
                break
            px, py = path[i - 1]
            qx, qy = path[i]
            dx = qx - px
            dy = qy - py
            heading = math.atan2(dy, dx)
            dtheta = _normalize(heading - self._theta)
            if abs(dtheta) > 1e-3:
                self.move_to(0.0, 0.0, dtheta)
                self._theta = heading
            dist_m = math.hypot(dx, dy) * self.cell_size_m
            if dist_m > 1e-4:
                self.move_to(dist_m, 0.0, 0.0)
            if on_progress:
                on_progress(i, len(path) - 1)

    # ---------------------------------------------------- info
    @property
    def sdk_name(self):
        return self._sdk_name or "(not connected)"


def _normalize(angle: float) -> float:
    """Wrap angle to (-pi, pi]."""
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle <= -math.pi:
        angle += 2 * math.pi
    return angle
