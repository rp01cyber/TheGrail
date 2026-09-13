"""
Idempotent bootstrap: ensures the three groups exist, seeds the demo content
(the approved RDP page) so the site renders immediately after install.

Run:  python manage.py seed_demo
"""
from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand

from notes.models import (
    ExternalLink,
    Folder,
    GROUP_ADMIN,
    GROUP_JUNIOR,
    GROUP_SENIOR,
    Page,
    Tag,
)

KNOWLEDGE = """\
## Overview

RDP (Remote Desktop Protocol) can be leveraged for command execution in several
ways, depending on the target configuration and the access already held. This
page covers the common methods, what each requires, and the traces they leave.

## Key points

- RDP grants interactive access to a remote host, which can be driven toward command execution.
- Execution is possible through built-in Windows tooling, misconfigurations, or third-party utilities.
- Most often used during lateral movement, after initial access is established.
- Typically requires valid credentials, network reachability, or a weak setting.
- Leaves detectable artifacts in logs (Event IDs 4624, 4648, 4688 and related).

## Common methods

| Method | Description | Requirements | Notes |
|---|---|---|---|
| `xfreerdp` | Open-source RDP client with exec options. | Valid creds / network | Supports drive redirect, `/exec`. |
| `mstsc` | Built-in Windows RDP client. | Valid creds | Launches programs via a `.rdp` file. |
| PsExec (post-RDP) | Run commands after RDP access. | Local admin | Useful for pivoting. |
| Scheduled Tasks | Register a task to run your command. | Valid creds | Doubles as persistence. |
| RDP misconfig | Abuse weak/exposed RDP. | Network access | Check NLA, restrictions, exposure. |
"""

TESTING = """\
> **Authorised testing only.** Run these against systems you have written
> permission to assess. Expect Event IDs 4624/4648/4688 in the defender's SIEM.

### 1 — Authenticate with xfreerdp

```bash
xfreerdp /u:administrator /p:'Passw0rd!' /v:10.10.10.5 \\
  /drive:share,/tmp/loot /cert:ignore +clipboard
```

### 2 — Execute via a staged .rdp file (mstsc)

```powershell
Set-Content conn.rdp "full address:s:10.10.10.5`nalternate shell:s:cmd.exe"
mstsc .\\conn.rdp
```

### 3 — Post-RDP execution with PsExec

```cmd
psexec.exe \\\\10.10.10.6 -u CORP\\admin -p Passw0rd! cmd.exe
```

### Cleanup checklist

- Remove staged files from redirected drives and `%TEMP%`.
- Delete any scheduled tasks created during testing.
- Record affected hostnames and timestamps in the engagement page.
"""


class Command(BaseCommand):
    help = "Seed groups and demo content."

    def handle(self, *args, **opts):
        for name in (GROUP_ADMIN, GROUP_SENIOR, GROUP_JUNIOR):
            Group.objects.get_or_create(name=name)
        self.stdout.write(self.style.SUCCESS("Groups ensured: Administrator, Senior, Junior"))

        lm, _ = Folder.objects.get_or_create(name="Lateral Movement", parent=None)
        rdp, _ = Folder.objects.get_or_create(name="RDP Protocol", parent=lm)

        page, created = Page.objects.get_or_create(
            folder=rdp,
            slug="command-execution",
            defaults={
                "title": "RDP — Command Execution",
                "description": "Methods for achieving command execution over RDP — "
                "built-in tooling, common misconfigurations, and third-party utilities.",
                "knowledge_md": KNOWLEDGE,
                "testing_md": TESTING,
                "version": 1,
            },
        )
        if not created:
            page.knowledge_md, page.testing_md = KNOWLEDGE, TESTING
            page.save()

        for t in ("rdp", "lateral-movement", "windows", "command-execution", "remote-access"):
            tag, _ = Tag.objects.get_or_create(name=t)
            page.tags.add(tag)

        page.external_links.all().delete()
        for i, (label, url) in enumerate([
            ("Microsoft RDP documentation", "https://learn.microsoft.com/windows-server/remote/remote-desktop-services/"),
            ("xfreerdp on GitHub", "https://github.com/FreeRDP/FreeRDP"),
            ("ATT&CK T1021.001 — Remote Services: RDP", "https://attack.mitre.org/techniques/T1021/001/"),
        ]):
            ExternalLink.objects.create(page=page, label=label, url=url, order=i)

        self.stdout.write(self.style.SUCCESS(f"Demo page ready: {page.get_absolute_url()}"))
