FROM python:3.12-alpine

# Setting non-root user for security
RUN adduser -D -u 1000 sandbox
# Using numerical username as kubernetes doesn't run 'non-root' defined pods that have string name
USER 1000 
WORKDIR /home/sandbox

COPY --chown=sandbox:sandbox executor.py .

EXPOSE 5000 

CMD ["python","executor.py"]
