import subprocess

class Sandbox:
    def run_safe(self, command):
        try:
            result = subprocess.check_output(
                command, shell=True, stderr=subprocess.STDOUT, timeout=5
            )
            return {"success": True, "output": result.decode()}
        except Exception as e:
            return {"success": False, "error": str(e)}
