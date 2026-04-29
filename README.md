# Blender MCP

Claude AI가 MCP(Model Context Protocol)를 통해 Blender 3D를 직접 제어하는 도구입니다.

자연어로 명령하면 Claude가 Blender 씬에서 오브젝트 생성, 수정, 삭제, Python 코드 실행을 자동으로 수행합니다.

## 동작 방식

```
Claude Desktop
     │ MCP (stdio / HTTP·SSE)
     ▼
MCP Server (Python)          ← 이 저장소
     │ TCP Socket :9999
     ▼
Blender Add-on (Python)      ← 이 저장소
     │ bpy API
     ▼
Blender 씬
```

## 요구사항

| 항목 | 최소 버전 |
|------|----------|
| Blender | **4.2 이상** (5.x 지원 확인) |
| Python | 3.10 이상 (Blender 외부 MCP 서버용) |
| Claude Desktop | 최신 버전 |

---

## 설치 방법

### 1단계 — 저장소 클론

```bash
git clone https://github.com/nowcika/blender_mcp.git
cd blender_mcp
```

### 2단계 — MCP 서버 의존성 설치

```bash
pip install -r requirements.txt
```

> `requirements.txt` 내용: `mcp>=1.0.0`

### 3단계 — Blender Add-on 설치

Blender 5.x (Extension 방식):

1. Blender 상단 메뉴 → **Edit → Preferences → Add-ons**
2. 우측 상단 **드롭다운(⌄) → Install from Disk** 클릭
3. 저장소의 `addon/` 폴더를 zip으로 압축

   ```bash
   # 프로젝트 루트에서 실행
   zip -r blender_mcp_addon.zip addon/
   ```

4. 압축된 `blender_mcp_addon.zip` 선택 후 **Install Add-on** 클릭
5. 목록에서 **"Blender MCP"** 항목 체크(활성화)

### 4단계 — Blender에서 소켓 서버 시작

1. Blender **3D Viewport** → 우측 **N** 키 → **MCP** 탭
2. **Start MCP Server** 버튼 클릭
3. 상태가 `Running` 으로 변경되면 준비 완료

> 기본 포트: `9999`. 변경하려면 환경변수 설정:
> ```bash
> BLENDER_MCP_PORT=9998  # Blender 실행 전 설정
> ```

---

## Claude Desktop 연동 (stdio — 권장)

`claude_desktop_config.json` 파일에 아래 내용을 추가합니다.

**파일 위치:**
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "blender": {
      "command": "python3",
      "args": ["-m", "server", "--transport", "stdio"],
      "cwd": "/절대경로/blender_mcp"
    }
  }
}
```

> `/절대경로/blender_mcp` 를 실제 클론 경로로 변경하세요.  
> Windows 예시: `"cwd": "C:\\Users\\yourname\\blender_mcp"`

설정 후 **Claude Desktop을 재시작**합니다.

---

## HTTP/SSE 모드 (원격 접속)

로컬이 아닌 원격 서버에서 Blender를 제어할 때 사용합니다.

```bash
# MCP 서버를 HTTP 모드로 실행
python3 -m server --transport http --host 0.0.0.0 --port 8080
```

Claude Desktop 설정:

```json
{
  "mcpServers": {
    "blender": {
      "url": "http://서버IP:8080/sse"
    }
  }
}
```

---

## 사용 가능한 MCP 도구

Claude와 대화 시 아래 도구들이 자동으로 활성화됩니다.

| 도구 | 설명 | 예시 명령 |
|------|------|---------|
| `create_object` | 오브젝트 생성 | "빨간 큐브 만들어줘" |
| `modify_object` | 위치·회전·크기 수정 | "큐브를 위로 2m 올려줘" |
| `delete_object` | 오브젝트 삭제 | "Cube 지워줘" |
| `execute_python` | Python 코드 실행 | "모든 오브젝트 이름 출력해줘" |
| `get_scene_info` | 씬 전체 정보 조회 | "지금 씬에 뭐가 있어?" |
| `get_object_info` | 특정 오브젝트 정보 | "Cube의 위치가 어디야?" |

### 사용 예시

Claude Desktop 채팅창에서:

```
큐브 하나 만들어줘
→ Claude가 create_object 도구 호출 → Blender에 Cube 생성

방금 만든 큐브를 (3, 0, 1)로 이동하고 45도 회전해줘
→ Claude가 modify_object 호출 → 위치·회전 적용

현재 씬에 있는 모든 오브젝트 목록 알려줘
→ Claude가 get_scene_info 호출 → 오브젝트 목록 반환
```

---

## 환경변수 설정

| 변수 | 기본값 | 설명 |
|------|-------|------|
| `BLENDER_MCP_PORT` | `9999` | Blender Add-on 소켓 포트 |
| `BLENDER_MCP_HOST` | `localhost` | MCP 서버가 연결할 Blender 호스트 |

---

## 문제 해결

### "Blender is not running" 오류

- Blender가 실행 중인지 확인
- N-Panel → MCP → **Start MCP Server** 버튼을 눌렀는지 확인
- 방화벽이 포트 9999를 차단하고 있지 않은지 확인

### Add-on이 목록에 나타나지 않을 때

- Blender 버전이 4.2 이상인지 확인
- `addon/` 폴더가 정상적으로 zip 압축되었는지 확인 (`addon/` 내부 파일이 zip 루트에 있어야 함)

```bash
# 올바른 압축 방법
cd addon
zip -r ../blender_mcp_addon.zip .
cd ..
```

### MCP 서버 연결 안 될 때

```bash
# 의존성 확인
pip show mcp

# 서버 직접 테스트 (stdio 대신 로그 확인용)
python3 -m server --transport http --port 8080
# http://localhost:8080/sse 접근해서 응답 확인
```

---

## 프로젝트 구조

```
blender_mcp/
├── addon/
│   ├── __init__.py           # Blender Add-on + 소켓 서버
│   ├── executor.py           # bpy 명령 실행기
│   └── blender_manifest.toml # Blender 5.x Extension 매니페스트
├── server/
│   ├── __init__.py           # MCP 서버 진입점 (stdio / HTTP)
│   ├── tools.py              # MCP 도구 6개 정의
│   └── blender_client.py     # Blender 소켓 클라이언트
├── requirements.txt
└── README.md
```

## 라이선스

GPL-3.0-or-later
