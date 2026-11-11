"""Patch multi-instance HA pour aldes-bridge; échec explicite si l'amont change."""
from pathlib import Path


def replace_once(text, old, new):
    if text.count(old) != 1:
        raise SystemExit(f"Patch incompatible avec cette version amont: {old!r}")
    return text.replace(old, new, 1)


client_path = Path('/app/server/ha/client.py')
discovery_path = Path('/app/server/ha/discovery_config.py')
client = client_path.read_text()
discovery = discovery_path.read_text()
client = replace_once(client, 'import os\n', 'import os\nimport re\n')
client = replace_once(client, '        self.prefix = prefix\n', '''        instance = os.environ.get("ALDES_INSTANCE_ID", "").strip()
        if instance and not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,31}", instance):
            raise ValueError("ALDES_INSTANCE_ID: 1-32 caracteres a-z, 0-9, _ ou -")
        self.prefix = f"{prefix}/{instance}" if instance else prefix
        self._ha_device_id = f"aldes_bridge_{instance}" if instance else "aldes_bridge"
        self._ha_client_id = f"aldes-ha-{instance}" if instance else "aldes-ha-discovery"
        _log.info("HA MQTT instance=%s prefix=%s client_id=%s device_id=%s",
                  instance or "legacy", self.prefix, self._ha_client_id, self._ha_device_id)
''')
client = replace_once(client, '                "aldes-ha-discovery",\n', '                self._ha_client_id,\n')
client = replace_once(client, '            self._device_id, profile, self.prefix, data,\n', '            self._ha_device_id, profile, self.prefix, data,\n')
discovery = replace_once(discovery, '    return configs\n', '''    # Les topics de discovery d'origine sont statiques: isoler aussi les
    # suppressions (payload vide), pas uniquement les annonces JSON.
    if device_id.startswith("aldes_bridge_"):
        scoped_configs = []
        for topic, payload in configs:
            root, component, object_id, config_leaf = topic.split("/")
            topic = f"{root}/{component}/{device_id}/{object_id}/{config_leaf}"
            if payload:
                config = json.loads(payload)
                config["device"]["name"] = f"Aldes T.ONE {device_id.removeprefix('aldes_bridge_')}"
                payload = json.dumps(config, ensure_ascii=False)
            scoped_configs.append((topic, payload))
        return scoped_configs
    return configs
''')
compile(client, str(client_path), 'exec')
compile(discovery, str(discovery_path), 'exec')
client_path.write_text(client)
discovery_path.write_text(discovery)
print('Patch multi-instance MQTT applique avec succes')
