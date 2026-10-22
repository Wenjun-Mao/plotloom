"""Registered no-work proof entry; no paid authority is available here."""
from handoff_qa import admit


def main():
    qa = admit("outer")
    from handoff_launch import launch
    return launch("handoff_proof_only", qa)


if __name__ == "__main__":
    main()
