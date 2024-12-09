from workflows import chunk_and_convert

workflow {
    splitLetters | flatten | convertToUpper | view { v -> v.trim() }
}