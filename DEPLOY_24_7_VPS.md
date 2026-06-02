# Deploy 24 Jam di VPS

Bot tidak bisa tetap order kalau laptop benar-benar mati. Solusi 24 jam adalah menjalankan project ini di VPS/cloud server yang terus menyala. File di folder `deploy/` menyiapkan backend trading dan dashboard sebagai `systemd` service.

## Alur Cepat

1. Sewa VPS Ubuntu 22.04/24.04 kecil.
2. Upload/copy folder project ini ke VPS, contoh ke `/opt/crypto_ai_trader`.
3. Di VPS, masuk ke folder project:

```bash
cd /opt/crypto_ai_trader
cp .env.vps.example .env
nano .env
```

4. Isi `GROQ_API_KEY`, `BINANCE_API_KEY`, `BINANCE_SECRET_KEY`, symbol, dan batas risiko.
5. Install service:

```bash
chmod +x deploy/*.sh
./deploy/install_vps_systemd.sh
```

6. Jalankan dulu mode paper:

```bash
sudo systemctl start crypto-ai-backend crypto-ai-dashboard
./deploy/status_vps.sh
```

7. Kalau paper sudah normal dan kamu memang mau real order:

```bash
./deploy/enable_live_vps.sh
```

Script live akan menjalankan `main.py --preflight-live` dulu. Kalau preflight gagal, live tidak diaktifkan.

## Akses Dashboard

Installer default mengikat dashboard ke `127.0.0.1:8501` di VPS, jadi tidak terbuka publik.

Dari laptop, buka tunnel:

```bash
ssh -L 8501:127.0.0.1:8501 user@IP_VPS
```

Lalu buka:

```text
http://127.0.0.1:8501
```

Kalau nanti dashboard mau dibuka via domain, set `DASHBOARD_PASSWORD` di `.env` dan pakai reverse proxy/Cloudflare Tunnel. Jangan expose port 8501 publik tanpa password.

## Perintah Penting

```bash
./deploy/status_vps.sh
sudo systemctl restart crypto-ai-backend crypto-ai-dashboard
./deploy/paper_vps.sh
./deploy/stop_vps.sh
```

Mode darurat dari dashboard akan menulis `EMERGENCY_STOP=true` ke `.env`. Backend membaca flag itu saat loop berjalan.

## Live Trading Checklist

- Binance API key punya izin futures yang sesuai.
- Withdrawal permission harus off.
- IP restriction Binance sebaiknya diisi IP VPS.
- `MAX_LIVE_ORDER_USDT` kecil dulu.
- `MAX_OPEN_POSITIONS=1` dulu.
- `MAX_LEVERAGE=1` dulu.
- `DASHBOARD_PASSWORD` diisi kalau dashboard bisa diakses dari internet.
- Cek `./deploy/status_vps.sh` setelah restart.

## Catatan Database

Database tetap SQLite di VPS:

```text
crypto_trader.db
```

Backend dan dashboard membaca file database yang sama melalui:

```text
DATABASE_URL=sqlite:///./crypto_trader.db
```

Backup sederhana:

```bash
cp crypto_trader.db "crypto_trader.$(date +%Y%m%d_%H%M%S).db"
```
