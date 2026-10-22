"""Fixed finite-pair launcher; source presence supplies no generation authority."""
from handoff_qa import admit


def main():
    qa=admit('outer')
    from handoff_launch import launch
    return launch('qualification_pair',qa)


if __name__=='__main__':
    main()
