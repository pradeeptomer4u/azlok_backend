#!/usr/bin/env python3
"""
Script to run database migrations.
"""
from app.utils.db_migration import run_migration

if __name__ == "__main__":
    run_migration()
