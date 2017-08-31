import logging
import sys
import argparse

from dataactcore.interfaces.db import GlobalDB
from dataactcore.logging import configure_logging
from dataactbroker.fsrs import config_valid, fetch_and_replace_batch, GRANT, PROCUREMENT
from dataactvalidator.health_check import create_app


logger = logging.getLogger(__name__)


if __name__ == '__main__':
    configure_logging()

    parser = argparse.ArgumentParser(description='Pull data from the FPDS Atom Feed.')
    parser.add_argument('-p', '--procurement_only', help='Get ONLY fsrs procurement data', action='store_true')
    parser.add_argument('-g', '--grants_only', help='Get ONLY fsrs grant data', action='store_true')
    args = parser.parse_args()
    if args.procurement_only and args.grants_only:
        logger.error("You cannot run the script with both -p and -g, only one or none.")
        sys.exit(1)
    with create_app().app_context():
        sess = GlobalDB.db().session
        if not config_valid():
            logger.error("No config for broker/fsrs/[service]/wsdl")
            sys.exit(1)
        else:
            awards = ['Starting']
            while len(awards) > 0:
                procs = fetch_and_replace_batch(sess, PROCUREMENT) if not args.grants_only else []
                grants = fetch_and_replace_batch(sess, GRANT) if not args.procurement_only else []
                # awards = procs + grants
                # numSubAwards = sum(len(a.subawards) for a in awards)
                # logger.info("Inserted/Updated %s awards, %s subawards", len(awards), numSubAwards)
