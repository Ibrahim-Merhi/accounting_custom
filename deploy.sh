#!/usr/bin/env bash
set -Eeuo pipefail

SITE="${1:-}"
BENCH_DIR="${2:-/home/frappe/frappe-bench}"
APP_NAME="accounting_custom"
APP_BRANCH="${ACCOUNTING_CUSTOM_BRANCH:-develop}"
APP_URL="${ACCOUNTING_CUSTOM_REPO:-https://github.com/Ibrahim-Merhi/accounting_custom.git}"

if [[ -z "$SITE" ]]; then
	echo "Usage: deploy.sh <site-name> [bench-directory]" >&2
	exit 2
fi

cd "$BENCH_DIR"

if [[ -d "apps/$APP_NAME/.git" ]]; then
	git -C "apps/$APP_NAME" fetch origin "$APP_BRANCH"
	git -C "apps/$APP_NAME" checkout "$APP_BRANCH"
	git -C "apps/$APP_NAME" pull --ff-only origin "$APP_BRANCH"
else
	bench get-app --branch "$APP_BRANCH" "$APP_URL"
fi

if ! bench --site "$SITE" list-apps | grep -qx "$APP_NAME"; then
	bench --site "$SITE" install-app "$APP_NAME"
fi

bench --site "$SITE" migrate
bench build --app "$APP_NAME"
bench --site "$SITE" clear-cache
bench --site "$SITE" execute accounting_custom.verification.assert_accounting_program

if command -v supervisorctl >/dev/null 2>&1; then
	sudo supervisorctl restart frappe-bench-web: frappe-bench-workers:
fi

echo "Accounting Custom deployment completed for $SITE."
