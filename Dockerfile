FROM python:3.11-slim
WORKDIR /app
COPY app.py .
ENV PORT=8080
ENV API_KEY=sk-render-arena-free
EXPOSE 8080
CMD ["python", "app.py"]
