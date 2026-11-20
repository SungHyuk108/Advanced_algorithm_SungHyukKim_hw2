# 과제2 · 에이전트와 함께 만드는 URL 단축기

2026-2 **고급알고리즘**(SIT2001-01) 과제2의 **시작 저장소**입니다.
채팅창에 묻고 복사·붙여넣기 하던 방식에서 벗어나, Codespace 안의 에이전트가
저장소를 읽고, 파일을 고치고, 테스트를 직접 돌리게 하는 방법을 익힙니다.

- 과제 안내: [lec-algorithm.github.io/lecture/article/hw2-2026](https://lec-algorithm.github.io/lecture/article/hw2-2026/)
- 수업 슬라이드: [lec-algorithm.github.io/lecture/slides/hw2-2026](https://lec-algorithm.github.io/lecture/slides/hw2-2026/)
- 해시 테이블 복습: [주제 08 해시 테이블](https://lec-algorithm.github.io/lecture/course/topic-08-hashing/)

## 시작하기

1. 이 저장소 상단의 **Use this template** → **Create a new repository**
2. 저장소 이름은 `algorithms-hw2`처럼 정합니다. 공개(Public)로 만듭니다.
3. 만들어진 **내 저장소**에서 **Code** → **Codespaces** 탭 → **Create codespace on main**
4. 왼쪽 막대의 Copilot 아이콘을 눌러 채팅 창을 열고, 창 아래쪽에서 **Agent** 모드를 고릅니다.

## 들어 있는 것

| 파일 | 하는 일 |
| --- | --- |
| `SPEC.md` | 명세 틀. 에이전트가 초안을 쓰고 **본인이 고칩니다** |
| `src/` · `tests/` · `experiments/` | 비어 있습니다. 수업에서 채웁니다 |
| `tools/catchup.sh` | 수업 중 놓친 단계를 따라잡는 스크립트 |
| `Makefile` | `make test` · `make serve` · `make experiment` · `make compare-experiment` |

`SPEC.md`는 수업 중 교수님 안내에 따라 에이전트가 초안을 작성하고, 내가 내용을 검토해 구현 기준으로 확정했다. 별도로 직접 수정한 커밋은 없으며, 실제 구현은 이 명세를 기준으로 진행했다.

정답 코드는 들어 있지 않습니다. 에이전트는 작업 공간의 파일을 읽으므로, 정답이
옆에 있으면 그대로 베껴 와서 연습이 되지 않습니다.

## 명령

컨테이너 안(Codespaces 터미널)에서 실행합니다.

| 하고 싶은 것 | 명령 |
| --- | --- |
| 테스트 | `make test` |
| 웹 서버 (포트 8000, 개별 체이닝) | `make serve` |
| 웹 서버 (포트 8000, 선형 탐지) | `make serve TABLE=linear` |
| 충돌 실험 | `make experiment` |
| 두 해시 테이블 비교 | `make compare-experiment` |
| 놓친 단계 따라잡기 | `sh tools/catchup.sh <단계 번호>` |

기본 서버의 `/table` 화면에는 개별 체이닝용 샘플 URL 30개가 들어 있습니다. 용량
64에서 5개 버킷에 충돌이 생기며, 가장 긴 연결 리스트는 2개 노드입니다. 노드 간
화살표로 버킷별 체이닝을 확인할 수 있습니다.

상단의 새 창 링크에서 여는 `/table/linear`는 체이닝과 데이터·단축 코드 경로가
분리된 선형 탐지 데모 테이블입니다. 이 화면에도 별도의 URL 30개가 들어 있고, 전체
64개 슬롯을 접지 않은 표로 나열해 각 URL의 시작 칸·이동 거리·실제 조사 순서를
보여 줍니다. 두 표는 동일한 URL을 공유하지 않습니다. 선형 탐지 화면은 별도 데이터로
동작하며, 여기서 URL을 추가해 확인한다. 각 화면의 폼으로 해당 테이블에
URL을 더 추가할 수 있으며, 선형 단축 링크는 `/linear/<코드>`를 사용합니다.

외부 라이브러리는 쓰지 않습니다. Python 표준 모듈만으로 충분합니다.

## 로컬에서 하기

```sh
git clone https://github.com/<본인 계정>/<내 저장소>.git
cd <내 저장소>
docker compose up -d
docker compose exec lab bash
```

컨테이너 안에서 `make serve`를 실행하면 호스트의 `http://localhost:8000`으로
접속할 수 있습니다. 8000번 포트가 이미 사용 중이면 컨테이너를 올릴 때 다른
포트를 지정하고, 서버는 컨테이너 안에서 평소처럼 실행합니다.

```sh
PORT=8080 docker compose up -d
docker compose exec lab bash
make serve
```

이 경우 `http://localhost:8080`으로 접속합니다. Codespaces에서는 전달된 포트
알림을 사용하면 됩니다. **이후 모든 `docker compose` 명령은 이 폴더에서 칩니다.**
