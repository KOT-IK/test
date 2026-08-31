import base64
import concurrent.futures
import socket
import time
import urllib.request
import socks  # Используется для проксирования запросов (pysocks)

# Источники публичных прокси
SOURCES = [
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/base64/vless",
    "https://raw.githubusercontent.com/yebekhe/TelegramV2rayCollector/main/sub/base64/hysteria2",
    "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Sub1.txt",
    "https://raw.githubusercontent.com/barry-far/V2ray-Configs/main/Sub2.txt",
    "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/sub/sub_merge.txt",
    "https://raw.githubusercontent.com/mft01/V2ray-Configs/main/All_Configs_Sub.txt",
    "https://raw.githubusercontent.com/ts-indexer/v2ray-collector/main/sub/vless.txt",
    "https://raw.githubusercontent.com/ts-indexer/v2ray-collector/main/sub/hysteria2.txt",
    "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/vless",
    "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/hysteria2",
    "https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/tuic",
    "https://raw.githubusercontent.com/erfanyern/v2ray-configs-collector/main/vless.txt",
    "https://raw.githubusercontent.com/erfanyern/v2ray-configs-collector/main/hysteria2.txt",
    "https://raw.githubusercontent.com/MrMohebi/xray-proxy-grabber-telegram/main/vless.txt",
    "https://raw.githubusercontent.com/Bardiafa/v2ray-collector/main/vless.txt",
    "https://raw.githubusercontent.com/azadnet-key/v2ray/main/vless.txt",
    "https://raw.githubusercontent.com/ALIILAPRO/v2rayNG-Config/main/sub.txt",
]

ALLOWED_PROTOCOLS = ("vless://", "hysteria2://", "tuic://", "hy2://")
TIMEOUT_MS = 1000  # Максимальный пинг до Telegram в мс
MAX_WORKERS = 40   # Число параллельных потоков
TELEGRAM_CHECK_URL = "https://api.telegram.org"


def fetch_source(url):
    configs = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            content = resp.read().decode("utf-8", errors="ignore").strip()

            if not any(proto in content for proto in ALLOWED_PROTOCOLS):
                try:
                    missing_padding = len(content) % 4
                    if missing_padding:
                        content += "=" * (4 - missing_padding)
                    content = base64.b64decode(content).decode(
                        "utf-8", errors="ignore"
                    )
                except Exception:
                    pass

            for line in content.splitlines():
                line = line.strip()
                if line.startswith(ALLOWED_PROTOCOLS):
                    configs.append(line)
    except Exception:
        pass
    return configs


def parse_host_port(config_url):
    try:
        if "://" in config_url:
            body = config_url.split("://")[1]
            main_part = body.split("@")[-1].split("?")[0].split("#")[0]
            if ":" in main_part:
                host, port = main_part.rsplit(":", 1)
                host = host.strip("[]")
                return host, int(port)
    except Exception:
        pass
    return None, None


def check_node(cfg):
    # Фильтруем типы, нестойкие к блокировкам
    if cfg.startswith("vless://"):
        if not ("security=reality" in cfg or "security=tls" in cfg):
            return None

    host, port = parse_host_port(cfg)
    if not host or not port:
        return None

    # Проверка подключения к Telegram через прокси
    start = time.perf_counter()
    try:
        # Создаем прокси-сокет
        s = socks.socksocket()
        s.set_proxy(socks.SOCKS5, host, port)
        s.settimeout(TIMEOUT_MS / 1000.0)

        # Пробуем подключиться к Telegram API напрямую
        s.connect(("api.telegram.org", 443))
        s.close()

        latency = (time.perf_counter() - start) * 1000
        if latency < TIMEOUT_MS:
            return cfg
    except Exception:
        pass
    return None


def main():
    print("Сбор ссылок из источников...")
    raw_configs = set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
        results = executor.map(fetch_source, SOURCES)
        for res in results:
            raw_configs.update(res)

    print(f"Собрано узлов: {len(raw_configs)}. Проверка доступности Telegram...")

    valid_configs = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(check_node, raw_configs)
        for res in results:
            if res:
                valid_configs.append(res)

    print(f"Отобрано рабочих узлов до Telegram (< {TIMEOUT_MS}мс): {len(valid_configs)}")

    payload = "\n".join(valid_configs)
    b64_sub = base64.b64encode(payload.encode("utf-8")).decode("utf-8")

    with open("sub.txt", "w", encoding="utf-8") as f:
        f.write(b64_sub)


if __name__ == "__main__":
    main()
