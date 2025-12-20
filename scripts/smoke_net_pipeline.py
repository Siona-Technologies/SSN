import os
from ssn.bootstrap import create_siona


def main() -> None:
    orch = create_siona()

    # 1) fetch
    fr = orch.tools.run(
        name="net.fetch",
        role="OWNER",
        deps={"role": "OWNER", "tools": orch.tools},
        args={"url": "https://example.com/", "max_bytes": 50000, "timeout_s": 10},
    )
    print("fetch ok:", fr.ok)
    print("fetch note:", (fr.data or {}).get("note"))
    print("fetch preview:", ((fr.data or {}).get("content") or "")[:160])
    if not fr.ok:
        print("fetch err:", fr.error)
        return

    # 2) sanitize
    sr = orch.tools.run(
        name="net.sanitize",
        role="OWNER",
        deps={"role": "OWNER", "tools": orch.tools},
        args={
            "url": fr.data["url"],
            "content_type": fr.data["content_type"],
            "content": fr.data["content"],
            "max_bytes": 50000,
        },
    )
    print("sanitize ok:", sr.ok)
    print("sanitize preview:", ((sr.data or {}).get("clean_text") or "")[:160])
    if not sr.ok:
        print("sanitize err:", sr.error)
        return

    # 3) cite
    cr = orch.tools.run(
        name="net.cite",
        role="OWNER",
        deps={"role": "OWNER", "tools": orch.tools},
        args={
            "url": fr.data["url"],
            "clean_text": (sr.data or {}).get("clean_text", ""),
            "title": "example.com",
            "snippet": "",
            "retrieved_at": (fr.data or {}).get("fetched_at", 0),
            "content_type": fr.data["content_type"],
        },
    )
    print("cite ok:", cr.ok)
    print("cite keys:", sorted(list((cr.data or {}).keys())))
    if not cr.ok:
        print("cite err:", cr.error)
        return


if __name__ == "__main__":
    # For LIVE testing, ensure offline is not forcing mock.
    os.environ.pop("SSN_OFFLINE", None)
    main()
