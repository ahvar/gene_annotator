#!/usr/bin/env python3
"""
GATE: Gene Annotation Transformative Engine
"""
import typer
import logging
import datetime
import os
from pathlib import Path
from typing_extensions import Annotated
from utils.pipeline_utils import validate_gate_output_dir

app = typer.Typer(pretty_exceptions_enable=False)
# pretty_exceptions_enable=False use in dev for black and white

__version__ = "1.0.0"
__copyright__ = (
    "Copyright \xa9 2023 Bristol Myers Squibb | "
    "Informatics and Predictive Sciences. All rights reserved.".encode(
        "utf-8", "ignore"
    )
)
__Application__ = "GATE"
GATE_LOGGER_NAME = __Application__ + "__" + __version__ + "_" + "gate"

gate_logger = logging.getLogger(GATE_LOGGER_NAME)


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def main(
    ctx: typer.Context,
    output_dir: Path = typer.Option(
        None,
        "-o",
        "--output-directory",
        exists=True,
        file_okay=True,
        dir_okay=False,
        writable=True,
        callback=validate_gate_output_dir,
        help="The manifest file",
    ),
    debug: bool = typer.Option(
        False,
        "-b",
        "--debug",
        help="Set log level to debug",
    ),
):
    """
    GATE v1.0.0:
    This application is designed to read gene annotation data, identify duplicate entries, and report gene counts.
    """

    try:
        timestamp = datetime.datetime.utcnow().strftime("%Y_%m_%dT%H_%M_%SZ")
        if debug:
            log_level = logging.DEBUG
        else:
            log_level = logging.INFO

        # set up output_dir
        gate_output_dir = gate_output_dir / f"svrna_results_{timestamp}"
        svrna_output_dir.mkdir()

        input_reader = InputReader(mage_results_dir, bard_results_dir, manifest)

        logging_file = f"{__Application__}_{timestamp}.log"
        log_dir = Path("/opt/ea/log") / __Application__
        log_dir.mkdir(exist_ok=True)
        app_log = LoggingUtils(
            applicationName=f"{__Application__} {__version__}",
            logFile=log_dir / logging_file,
            fileLevel=log_level,
            consoleLevel=logging.ERROR,
        )
        app_log.logApplicationStart()
        auditor_log = AuditorLog(__Application__, __version__)
        auditor_log_path = svrna_output_dir
        auditor_log.addOutput(f"{os.path.join(log_dir, logging_file)}")

        # get manifest data
        mapping_and_manifest_utils = MappingAndManifestUtils(input_reader)
        [
            manifest_df,
            sample_list,
        ] = mapping_and_manifest_utils.collect_required_columns()

        # collect data and write to ouptut files
        if tier == regulatory_tier["ruo"]:
            hla = HLADataHandler(input_reader)
            hla.lookup_hla_type_and_populate_pforres()
            hla.write_blood_rna_seq_hla_types(svrna_output_dir, tier, timestamp)

        cytogenetic_mutations = CytogeneticMutations(
            input_reader, fusions_roi_file, fusions_static_file, sample_list
        )
        cytogenetic_mutations.write_to_csv(
            svrna_output_dir, manifest_df, tier, timestamp
        )
        rna_seq = RnaSeq(input_reader, rna_seq_static_file, sample_list)
        rna_seq.write_to_csv(svrna_output_dir, manifest_df, tier, timestamp)
        translocations = Translocations(
            input_reader,
            fusions_roi_file,
            fusions_static_file,
            sample_list,
            svrna_output_dir,
            fasta,
        )

        SomaticMutations(
            small_variant_gene_static_file, sample_list, input_reader, svrna_output_dir
        )

    except LogFileCreationError as lfe:
        set_error_and_exit("Unable to create log file: {}".format(lfe.filespec))
    except Exception as err:
        set_error_and_exit(f"Unable to initiate Application and Auditor logs: {err}")
    finally:
        auditor_log.setCompletionTime()
        if auditor_log_path:
            auditor_log.writeLogFile(auditor_log_path)
        app_log.logApplicationFinish()


if __name__ == "__main__":
    app()
