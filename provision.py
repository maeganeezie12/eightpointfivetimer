import argparse
import secrets

import db

db.init_db()


def generate_password() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(4))


def cmd_add(args):
    password = args.password or generate_password()
    db.add_user(args.name, password, args.duration_hours)
    print(f"Added user '{args.name}'.")
    print(f"Password (give this to them — it won't be shown again): {password}")


def cmd_list(args):
    for user in db.list_users():
        duration = user["duration_hours"] or "default"
        print(f"- {user['name']} (duration_hours={duration}, created_at={user['created_at']})")


def cmd_remove(args):
    removed = db.remove_user_by_name(args.name)
    if removed:
        print(f"Removed {removed} user(s) named '{args.name}' and their checkins.")
    else:
        print(f"No user named '{args.name}' found.")


def cmd_set_password(args):
    password = args.password or generate_password()
    changed = db.set_password_by_name(args.name, password)
    if changed:
        print(f"Updated password for '{args.name}': {password}")
    else:
        print(f"No user named '{args.name}' found.")


def main():
    parser = argparse.ArgumentParser(description="Manage work_timer_server users")
    sub = parser.add_subparsers(dest="command", required=True)

    add_parser = sub.add_parser("add", help="Add a new user and print their password")
    add_parser.add_argument("name")
    add_parser.add_argument("--duration-hours", type=float, default=None)
    add_parser.add_argument("--password", default=None, help="Custom password; auto-generates a 4-digit PIN if omitted")
    add_parser.set_defaults(func=cmd_add)

    list_parser = sub.add_parser("list", help="List provisioned users")
    list_parser.set_defaults(func=cmd_list)

    remove_parser = sub.add_parser("remove", help="Remove a user (and their checkins) by name")
    remove_parser.add_argument("name")
    remove_parser.set_defaults(func=cmd_remove)

    setpw_parser = sub.add_parser("set-password", help="Change an existing user's password")
    setpw_parser.add_argument("name")
    setpw_parser.add_argument("password", nargs="?", default=None, help="New password; auto-generates a 4-digit PIN if omitted")
    setpw_parser.set_defaults(func=cmd_set_password)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
