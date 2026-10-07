import os
import json
from datetime import datetime
from typing import List, Dict, Any, Callable
from core.skill import Skill

class ScreenshotSkill(Skill):
    """Skill for taking screenshots across Windows and other operating systems."""

    def __init__(self):
        # Default screenshot directory
        self.screenshot_dir = os.path.join(os.path.expanduser("~"), "Desktop", "JARVIS_Screenshots")
        os.makedirs(self.screenshot_dir, exist_ok=True)

    @property
    def name(self) -> str:
        return "screenshot_skill"

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "take_screenshot",
                    "description": "Capture a screenshot of the entire computer display and save it to the desktop.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "string",
                                "description": "Optional custom filename (without extension)."
                            }
                        },
                        "required": []
                    }
                }
            }
        ]

    def get_functions(self) -> Dict[str, Callable]:
        return {
            "take_screenshot": self.take_screenshot
        }

    def take_screenshot(self, filename: str = None) -> str:
        try:
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"screenshot_{timestamp}"

            if not filename.endswith('.png'):
                filename += '.png'

            filepath = os.path.join(self.screenshot_dir, filename)

            # Try PIL ImageGrab
            captured = False
            try:
                from PIL import ImageGrab
                img = ImageGrab.grab()
                img.save(filepath)
                captured = True
            except Exception:
                pass

            if not captured:
                # Try PyAutoGUI
                try:
                    import pyautogui
                    pyautogui.screenshot(filepath)
                    captured = True
                except Exception:
                    pass

            if captured and os.path.exists(filepath):
                return json.dumps({
                    "status": "success",
                    "message": "Screenshot saved successfully",
                    "path": filepath
                })
            else:
                return json.dumps({
                    "status": "error",
                    "message": "Failed to capture screenshot with available display drivers"
                })

        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Screenshot error: {str(e)}"
            })
