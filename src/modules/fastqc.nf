process runFastQC {
    container 'biocontainers/fastqc:latest'
    
    input:
    path raw_reads

    output:
    path "fastqc_reports/*"

    script:
    """
    mkdir -p fastqc_reports
    fastqc -o fastqc_reports $raw_reads
    """
}
