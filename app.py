#!/usr/bin/env python3
#USE VENV: source venv/bin/activate
"""
Run script for the Asset Management System
"""

from app import create_app
from app.build import build_database
from app.logger import get_logger
import sys
import argparse

app = create_app()
logger = get_logger("asset_management.run")

def parse_arguments():
    """Parse command line arguments for build phases"""
    parser = argparse.ArgumentParser(description='Asset Management System')
    parser.add_argument('--phase1', action='store_true', 
                       help='Build only Phase 1 (Core Foundation Tables and System Initialization)')
    parser.add_argument('--phase2', action='store_true', 
                       help='Build Phase 1 and Phase 2 (Core + Asset Detail Tables)')
    parser.add_argument('--phase3', action='store_true', 
                       help='Build Phase 1, Phase 2, and Phase 3 (Core + Asset Detail Tables + Automatic Detail Creation)')
    parser.add_argument('--phase4', action='store_true', 
                       help='Build Phase 1, Phase 2, Phase 3, and Phase 4 (Core + Asset Detail Tables + Automatic Detail Creation + User Interface)')
    parser.add_argument('--build-only', action='store_true',
                       help='Build database tables only, do not insert data (except critical data). Critical data is ALWAYS checked and inserted regardless of flags.')
    parser.add_argument('--enable-debug-data', action='store_true', default=True,
                       help='Enable debug data insertion (default: enabled if flag not present)')
    parser.add_argument('--no-debug-data', action='store_false', dest='enable_debug_data',
                       help='Disable debug data insertion')
    
    return parser.parse_args()

if __name__ == '__main__':
    args = parse_arguments()
    
    logger.debug("Starting Asset Management System...")
    
    # Determine build phase based on arguments
    if args.phase1:
        logger.debug("=== Building Phase 1 Only ===")
        logger.debug("Phase 1A: Core Foundation Tables")
        logger.debug("Phase 1B: Core System Initialization")
        build_phase = 'phase1'
    elif args.phase2:
        logger.debug("=== Building Phase 1 and Phase 2 ===")
        logger.debug("Phase 1A: Core Foundation Tables")
        logger.debug("Phase 1B: Core System Initialization")
        logger.debug("Phase 2: Asset Detail Tables")
        build_phase = 'phase2'
    elif args.phase3:
        logger.debug("=== Building Phase 1, Phase 2, and Phase 3 ===")
        logger.debug("Phase 1A: Core Foundation Tables")
        logger.debug("Phase 1B: Core System Initialization")
        logger.debug("Phase 2: Asset Detail Tables")
        logger.debug("Phase 3: Automatic Detail Creation")
        build_phase = 'phase3'
    elif args.phase4:
        logger.debug("=== Building Phase 1, Phase 2, Phase 3, and Phase 4 ===")
        logger.debug("Phase 1A: Core Foundation Tables")
        logger.debug("Phase 1B: Core System Initialization")
        logger.debug("Phase 2: Asset Detail Tables")
        logger.debug("Phase 3: Automatic Detail Creation")
        logger.debug("Phase 4: User Interface & Authentication")
        build_phase = 'phase4'
    else:
        logger.debug("=== Building All Phases ===")
        logger.debug("Phase 1A: Core Foundation Tables")
        logger.debug("Phase 1B: Core System Initialization")
        logger.debug("Phase 2: Asset Detail Tables")
        logger.debug("Phase 3: Automatic Detail Creation")
        logger.debug("Phase 4: User Interface & Authentication")
        build_phase = 'all'
    logger.debug("")
    
    # Determine data phase and debug data flag
    # If --build-only, set data_phase to 'none' (only create tables, no data insertion except critical)
    if args.build_only:
        data_phase = 'none'
        logger.debug("--build-only mode: Creating tables only (critical data will still be verified/inserted)")
    elif args.phase1:
        data_phase = 'phase1'
    elif args.phase2:
        data_phase = 'phase2'
    elif args.phase3:
        data_phase = 'phase3'
    elif args.phase4:
        data_phase = 'phase4'
    else:
        data_phase = 'all'
    
    # Build database
    # Note: Critical data is ALWAYS checked and inserted regardless of flags
    build_database(
        build_phase=build_phase, 
        data_phase=data_phase,
        enable_debug_data=args.enable_debug_data if not args.build_only else False
    )
    
    if args.build_only:
        logger.debug("Build completed. Exiting without starting web server.")
        sys.exit(0)
    
    logger.debug("")
    logger.debug("Access the application at: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000) 