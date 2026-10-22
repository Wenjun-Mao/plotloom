"""Registered paid-Outline entry; actual use requires independent allocation."""
from handoff_qa import admit


def main():
    qa = admit("outer")
    from handoff_launch import launch
    return launch("paid_outline", qa)


if __name__ == "__main__":
    main()
