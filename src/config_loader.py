import os
from pathlib import Path
from typing import Any, Dict
import yaml

class Config:
    def __init__(self):
        self._data = {}
        self._load_yaml()
        self._apply_env()
        self._defaults()
        self._post_process()

    def _load_yaml(self):
        yaml_path = Path("config/config.yaml")
        if yaml_path.exists():
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    self._data = yaml.safe_load(f) or {}
                print(f"✅ 已加载配置: {yaml_path}")
            except Exception as e:
                print(f"⚠️ 加载配置失败: {e}")

    def _apply_env(self):
        for key, val in list(self._data.items()):
            env_val = os.getenv(key.upper())
            if env_val is not None:
                if isinstance(val, bool):
                    self._data[key] = env_val.lower() in ('true', '1', 'yes')
                elif isinstance(val, int):
                    self._data[key] = int(env_val)
                elif isinstance(val, float):
                    self._data[key] = float(env_val)
                elif isinstance(val, list):
                    self._data[key] = [x.strip() for x in env_val.split(',') if x.strip()]
                else:
                    self._data[key] = env_val

    def _defaults(self):
        defaults = {
            'root_dir': '.',
            'data_dir': 'data',
            'output_dir': 'output',
            'max_workers': 20,
            'timeout': 8,
            'http_timeout': 8,
            'ffmpeg_enable': True,
            'ffmpeg_mode': 'deep',
            'ffprobe_cache_hours': 168,
            'cache_hours': 24,
            'cache_raw_hours': 48,
            'cache_speed_hours': 24,
            'enable_demo_filter': True,
            'enable_alias': True,
            'enable_blacklist': True,
            'database_enable': True,
            'enable_incremental_fetch': True,
            'enable_json_output': True,
            'enable_lite_version': True,
            'enable_epg_output': True,
            'demo_match_mode': 'contains',
            'max_sources_per_channel': 3,
            'max_retry_before_blacklist': 2,
            'slow_speed_threshold': 3000,
            'download_chunk_size': 262144,
            'autonomous_mode': True,
            'auto_update_stable': True,
            'auto_replace_failed': True,
            'quality_check_interval': 24,
            'candidate_observation_hours': 24,
            'candidate_min_success': 3,
            'candidate_min_success_rate': 0.5,
            'candidate_max_latency': 3000,
            'auto_promote_threshold': 3,
            'health_history_days': 30,
            'predict_threshold': 0.6,
            'enable_fixed_optimization': True,
            'fixed_optimization_threshold': 200,
            'open_rtmp': False,
            'nginx_http_port': 8080,
            'nginx_rtmp_port': 1935,
            'rtmp_idle_timeout': 300,
            'rtmp_max_streams': 10,
            'rtmp_transcode_mode': 'copy',
            'open_epg': True,
            'open_subscribe_epg': True,
            'subscribe_file': 'config/subscribe.txt',
            'whitelist_file': 'config/whitelist.txt',
            'blacklist_file': 'config/blacklist.txt',
            'alias_file': 'config/alias.txt',
            'demo_file': 'config/demo.txt',
            'enable_github_proxy': False,
            'github_raw_proxies': [
                'https://ghproxy.net/',
                'https://gh-proxy.19860519.xyz/',
                'https://raw.kkgithub.com/',
            ],
            'github_proxy_timeout': 15,
            'raw_sources': [
                'https://raw.githubusercontent.com/iptv-org/iptv/refs/heads/master/streams/cn.m3u',
                'https://raw.githubusercontent.com/iptv-org/iptv/gh-pages/countries/cn.m3u',
                'https://raw.githubusercontent.com/vbskycn/iptv/master/tv/iptv4.txt',
                'https://raw.githubusercontent.com/zzgpy1/iptv-api/master/output/result.txt',
                'https://raw.githubusercontent.com/zzgpy1/Collect-IPTV/main/best_sorted.m3u',
                'https://raw.githubusercontent.com/zzgpy1/ipv6-iptv/master/tv/iptv4.txt',
                'https://raw.githubusercontent.com/CCSH/IPTV/refs/heads/main/live.txt',
                'https://raw.githubusercontent.com/kakaxi-1/IPTV/main/iptv.txt',
            ],
            'direct_sources': [
                'https://tv.19860519.xyz/xymm',
            ],
            'open_realtime_write': True,
        }
        for k, v in defaults.items():
            if k not in self._data or self._data[k] is None:
                self._data[k] = v

    def _post_process(self):
        for key in ['root_dir', 'data_dir', 'output_dir', 'subscribe_file', 'whitelist_file', 'blacklist_file', 'alias_file', 'demo_file']:
            if key in self._data:
                self._data[key] = Path(self._data[key])
        # 合并源列表
        raw = self._data.get('raw_sources', [])
        direct = self._data.get('direct_sources', [])
        self._data['iptv_sources'] = list(raw) + list(direct)

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def __getattr__(self, name):
        if name in self._data:
            return self._data[name]
        raise AttributeError(f"Config has no attribute '{name}'")

    def to_dict(self):
        return self._data.copy()

config = Config()
