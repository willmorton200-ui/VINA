#!/usr/bin/env bash
# ======================================================================
# VINA Scanner - Benchmark Evaluation Runner (Linux / macOS / WSL)
# ======================================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

ENDPOINT="${ENDPOINT:-http://127.0.0.1:8080/v1/eval/predict}"
TARGET="${1:-eval}"

if [ "$TARGET" = "1" ] || [ "$TARGET" = "2" ] || [ "$TARGET" = "119" ]; then
    echo "=== Запуск прогона $TARGET (owner_eval) ==="
    python3 test_vina_scanner.py --eval-root ./owner_eval --run "$TARGET" --endpoint "$ENDPOINT" --mode http "${@:2}"
elif [ "$TARGET" = "eval" ] || [ -d "$TARGET" ]; then
    EVAL_DIR="${TARGET}"
    [ "$EVAL_DIR" = "eval" ] && EVAL_DIR="./eval"
    echo "=== Запуск 100 контрольных бутылок ($EVAL_DIR) ==="
    python3 test_vina_scanner.py --eval-root "$EVAL_DIR" --endpoint "$ENDPOINT" --mode http "${@:2}"
else
    echo "Использование: $0 [eval | 1 | 2 | 119 | путь_к_папке] [--mode http|direct]"
    exit 1
fi
