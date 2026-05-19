import subprocess
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
import os

# Start a persistent REPL
REPL = subprocess.Popen(
    ["python3", "-i", "-q", "-u"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1 # Line buffered
)

# Disable the >>> and ... prompts
REPL.stdin.write("import sys; sys.ps1=''; sys.ps2=''\n")
REPL.stdin.flush()

class StreamingExecutorHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'
    def do_POST(self):
        if self.path == '/run':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            code = data.get("code", "")
            
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Transfer-Encoding', 'chunked')
            self.end_headers()

            delimiter = "___END_OF_EXECUTION___"
            
            with open("/tmp/script.py", "w") as f:
                f.write(code)
                
            # exec allows defining functions and variables globally in the REPL
            command = f"try:\n    exec(open('/tmp/script.py').read())\nexcept Exception as e:\n    import traceback; traceback.print_exc()\n\nprint('{delimiter}')\n"
            
            try:
                REPL.stdin.write(command)
                REPL.stdin.flush()

                while True:
                    line = REPL.stdout.readline()
                    if not line:
                        break # Process died
                        
                    if delimiter in line:
                        break # End of this execution run

                    chunk = line.encode('utf-8')
                    self.wfile.write(f"{len(chunk):X}\r\n".encode())
                    self.wfile.write(chunk + b"\r\n")
                    self.wfile.flush()

                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
                
            except Exception as e:
                err_msg = f"Execution Error: {str(e)}\n".encode('utf-8')
                self.wfile.write(f"{len(err_msg):X}\r\n".encode())
                self.wfile.write(err_msg + b"\r\n")
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()

if __name__ == "__main__":
    server = HTTPServer(('0.0.0.0', 5000), StreamingExecutorHandler)
    print("Persistent REPL Executor listening on port 5000...")
    server.serve_forever()