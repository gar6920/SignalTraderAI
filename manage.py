import os
import subprocess
import argparse

DATA_DIR = './data'

def ensure_data_dir():
    """Create the data directory if it doesn't exist."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"Created directory: {DATA_DIR}")

def is_linked():
    """Check if the linking has been completed."""
    return os.path.exists(os.path.join(DATA_DIR, '.linked'))

def link_signal_cli():
    """Start signal-cli in normal mode for initial linking."""
    ensure_data_dir()
    print("Starting signal-cli in normal mode for linking...")
    env = os.environ.copy()
    env['MODE'] = 'normal'
    subprocess.check_call(['docker-compose', 'up', '-d', 'signal-cli'], env=env)
    print("Please check the logs for the QR code: docker logs signal-cli-rest-api")
    print("Scan the QR code with your Signal app to link the device.")
    input("Press Enter after linking is complete...")
    subprocess.check_call(['docker-compose', 'down'])
    with open(os.path.join(DATA_DIR, '.linked'), 'w') as f:
        f.write('linked')
    print("Linking complete.")

def start_application():
    """Start all Docker containers after ensuring linking is done."""
    ensure_data_dir()
    if not is_linked():
        link_signal_cli()
    print("Starting Docker containers...")
    subprocess.check_call(['docker-compose', 'up', '--build', '-d'])

def stop_application():
    """Stop all Docker containers."""
    print("Stopping Docker containers...")
    subprocess.check_call(['docker-compose', 'down'])

def main():
    """Parse command-line arguments and execute the specified action."""
    parser = argparse.ArgumentParser(description="Manage Signal Bot Application")
    parser.add_argument('action', choices=['link', 'start', 'stop'], help="Action to perform")
    args = parser.parse_args()

    if args.action == 'link':
        link_signal_cli()
    elif args.action == 'start':
        start_application()
    elif args.action == 'stop':
        stop_application()

if __name__ == '__main__':
    main()