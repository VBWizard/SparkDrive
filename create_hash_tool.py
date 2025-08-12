from passlib.hash import pbkdf2_sha256
import getpass
import sys

def hash_password(password):
    return pbkdf2_sha256.hash(password)

if __name__ == "__main__":
    try:
        password = getpass.getpass("Enter password: ")
        confirm = getpass.getpass("Confirm password: ")

        if password != confirm:
            print("Error: Passwords do not match.")
            sys.exit(1)

        print(hash_password(password))

    except KeyboardInterrupt:
        print("\nOperation cancelled.")
        sys.exit(1)
