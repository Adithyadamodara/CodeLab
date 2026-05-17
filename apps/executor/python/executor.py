import subprocess
import json
from http.server import BaseHTTPRequestHandler, HTTPServer

class CodeExecutorHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/run':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            
            code = data.get("code", "")
            
            # Write code to a temporary file
            with open("/tmp/script.py", "w") as f:
                f.write(code)

            try:
                # Execute the code with a timeout to prevent infinite loops
                result = subprocess.run(
                    ["python3", "/tmp/script.py"],
                    capture_output=True,
                    text=True,
                    timeout=5  # Hard limit for execution time
                )
                response = {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "exit_code": result.returncode
                }
            except subprocess.TimeoutExpired:
                response = {"stdout": "", "stderr": "Error: Execution Timeout", "exit_code": 124}
            except Exception as e:
                response = {"stdout": "", "stderr": str(e), "exit_code": 1}

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

if __name__ == "__main__":
    server = HTTPServer(('0.0.0.0', 5000), CodeExecutorHandler)
    print("Executor listening on port 5000...")
    server.serve_forever()