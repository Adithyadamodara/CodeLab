import subprocess
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

class StreamingExecutorHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/run':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)
            code = data.get("code", "")
            
            # Write to the secure, writable mount
            with open("/tmp/script.py", "w") as f:
                f.write(code)

            # Send headers for streaming response
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.send_header('Transfer-Encoding', 'chunked') # Enables streaming chunks
            self.end_headers()

            try:
                # Launch process and pipe outputs
                process = subprocess.Popen(
                    ["python3", "-u", "/tmp/script.py"], # -u forces unbuffered stdout
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, # Merge stderr into stdout stream
                    text=True
                )

                # Read line by line as it prints
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        # Write in HTTP Chunked encoding format: [size in hex]\r\n[data]\r\n
                        chunk = line.encode('utf-8')
                        self.wfile.write(f"{len(chunk):X}\r\n".encode())
                        self.wfile.write(chunk + b"\r\n")
                        self.wfile.flush()

                # End chunked response
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
    print("Streaming Executor listening on port 5000...")
    server.serve_forever()