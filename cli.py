import sys
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

import argparse
from app import MaturityAssessmentApplication
from models import SSHCredentials


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="devsecops-assess",
        description="Система оценки зрелости DevSecOps-инфраструктуры",
    )
    parser.add_argument(
        "--ip", nargs="+", required=True, metavar="IP",
        help="IP-адрес(а) целевых узлов (можно несколько через пробел)"
    )
    parser.add_argument("--user", default="admin", metavar="USER", help="Имя пользователя SSH")
    parser.add_argument("--password", default=None, metavar="PASS", help="Пароль SSH")
    parser.add_argument("--key", default=None, metavar="PATH", help="Путь к приватному SSH-ключу")
    parser.add_argument(
        "--profile", default="default", choices=["user", "default", "admin"],
        help="Профиль аудита: user (2 проверки), default (4), admin (7, полный DevSecOps)"
    )
    parser.add_argument(
        "--format", default="json", choices=["json", "html"],
        help="Формат экспорта итогового отчёта"
    )
    parser.add_argument(
        "--output", default=None, metavar="FILE",
        help="Файл для сохранения отчёта (по умолчанию — stdout)"
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()

    creds = SSHCredentials(
        username=args.user,
        password=args.password,
        private_key_path=args.key,
    )

    app = MaturityAssessmentApplication()
    reports = app.initiate_maturity_assessment(
        ip_addresses=args.ip,
        ssh_credentials=creds,
        profile=args.profile,
    )

    if not reports:
        print("[ERROR] Оценка не выполнена — проверьте параметры", file=sys.stderr)
        sys.exit(1)

    for report in reports:
        content = app.export_report(report, format=args.format)
        if args.output:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(content)
            print(f"Отчёт сохранён: {args.output}")
        else:
            print(content)


if __name__ == "__main__":
    main()
