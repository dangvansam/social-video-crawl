# Social Video Downloader

A high-performance video downloading service with REST API and background task processing using Hatchet.

## Project Structure

```
social-video-crawl/
├── src/                        # Source code
│   ├── api_hatchet.py          # FastAPI API with Hatchet integration
│   ├── worker.py               # Background worker
│   └── social_video_downloader.py  # Core downloader logic
├── docker-compose.yml          # Docker services configuration
├── Dockerfile                  # Container image definition
├── requirements.txt            # Python dependencies
├── Makefile                    # Convenience commands
├── nginx.conf                  # Nginx configuration
└── README.md                   # Documentation
```

## Features

- Download videos, audio, and subtitles from multiple platforms using yt-dlp
- FastAPI-based REST API with async support
- Distributed task processing with Hatchet
- Docker containerization with Docker Compose
- Scalable worker architecture
- Nginx reverse proxy with rate limiting
- Comprehensive logging with Loguru

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Make (optional, for using Makefile commands)
- 4GB+ RAM recommended
- 10GB+ free disk space

### Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/social-video-crawl.git
cd social-video-crawl
```

2. Copy environment configuration:
```bash
cp .env.example .env
# Edit .env with your configuration
```

3. Start the services:
```bash
# Using Make
make up

# Or using Docker Compose directly
docker-compose up -d
```

## Deployment

### Development Environment

```bash
make dev
# or
docker-compose up -d
```

Services available:
- API: http://localhost:8003
- Nginx: http://localhost:8004

### Starting Services

```bash
# Start all services
docker-compose up -d

# Or start with logs visible
docker-compose up
```

## API Usage

### Single Video Download

```bash
curl -X POST http://localhost:8003/download \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/video",
    "video": true,
    "audio": true,
    "subtitles": true
  }'
```

### Batch Download

```bash
curl -X POST http://localhost:8003/batch \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://example.com/video1",
      "https://example.com/video2"
    ],
    "video": true,
    "audio": false,
    "subtitles": true
  }'
```

### Check Task Status

```bash
curl http://localhost:8003/task/{task_id}
```

### Extract Video Information

```bash
curl -X POST http://localhost:8003/info \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/video"}'
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Client    │────▶│    Nginx    │────▶│   FastAPI   │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │   Hatchet   │
                                        └─────────────┘
                                               │
                          ┌────────────────────┼────────────────────┐
                          ▼                    ▼                    ▼
                    ┌──────────┐        ┌──────────┐        ┌──────────┐
                    │ Worker 1 │        │ Worker 2 │        │ Worker N │
                    └──────────┘        └──────────┘        └──────────┘
                          │                    │                    │
                          └────────────────────┼────────────────────┘
                                               ▼
                                        ┌─────────────┐
                                        │  yt-dlp     │
                                        └─────────────┘
```

## Configuration

### Environment Variables

Key configuration options in `.env`:

```env
# API Configuration
API_PORT=8001
LOG_LEVEL=INFO
DOWNLOAD_DIR=/app/downloads

# Hatchet Configuration
HATCHET_CLIENT_TOKEN=your-token
HATCHET_API_URL=https://api.hatchet.run

# Workers
MAX_WORKERS=5
WORKER_ID=1
```

### Download Options

Downloads are organized as:
```
download/
├── YYYY-MM-DD/
│   ├── video-title-1/
│   │   ├── video.mp4
│   │   ├── audio.wav
│   │   ├── sub-en.vtt
│   │   └── sub-vie.vtt
│   └── video-title-2/
│       └── ...
```

## Scaling

### Scale Workers

```bash
# Scale to 10 workers
docker-compose up -d --scale worker=10

# Using Make
make scale-workers
```

### Performance Tuning

1. **Nginx Rate Limiting**: Configured in `nginx.conf`
2. **Worker Count**: Adjust `MAX_WORKERS` in `.env`
3. **Resource Limits**: Set in `docker-compose.yml`

## Maintenance

### View Logs

```bash
# All services
make logs

# Specific service
make logs-api
make logs-worker
```

### Clean Up

```bash
# Stop services and remove volumes
make clean

# Full Docker cleanup
make docker-clean
```

## Development

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run API locally
python src/api_hatchet.py

# Run worker locally
python src/worker.py
```

### Testing

```bash
# Run tests
make test

# Health check
make health
```

## Troubleshooting

### Common Issues

1. **Port already in use**
   ```bash
   # Change ports in docker-compose.yml or .env
   API_PORT=8003
   ```

2. **Disk space issues**
   ```bash
   # Clean up downloads
   rm -rf download/*
   make docker-clean
   ```

3. **Worker not processing tasks**
   ```bash
   # Check worker logs
   make logs-worker
   # Restart workers
   make restart-worker
   ```

## Security

- Non-root user in containers
- Rate limiting on API endpoints
- SSL/TLS support in Nginx
- Environment-based secrets management
- Network isolation between services

## Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:
- Create an issue on GitHub
- Check logs with `make logs`
- Review documentation in `/docs`