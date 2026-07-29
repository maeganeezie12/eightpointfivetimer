import argparse
import secrets

import db

db.init_db()


def cmd_add(args):
    token = secrets.token_urlsafe(24)
    db.add_user(args.name, token, args.duration_hours)
    print(f"Added user '{args.name}'.")
    print(f"Token (copy this now — it will not be shown again): {token}")


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


def main():
    parser = argparse.ArgumentParser(description="Manage work_timer_server users")
    sub = parser.add_subparsers(dest="command", required=True)

    add_parser = sub.add_parser("add", help="Add a new user and print their token")
    add_parser.add_argument("name")
    add_parser.add_argument("--duration-hours", type=float, default=None)
    add_parser.set_defaults(func=cmd_add)

    list_parser = sub.add_parser("list", help="List provisioned users")
    list_parser.set_defaults(func=cmd_list)

    remove_parser = sub.add_parser("remove", help="Remove a user (and their checkins) by name")
    remove_parser.add_argument("name")
    remove_parser.set_defaults(func=cmd_remove)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
