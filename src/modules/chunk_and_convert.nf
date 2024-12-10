params.pancakes = "Blueberry pancakes"

process splitLetters {
    output:
    path 'chunk_*'

    script:
    """
    printf "${params.pancakes}" | split -b 6 - chunk_
    """


}

process convertToUpper {
    input:
    path x


    output:
    stdout

    script:
    """
    cat $x
    """


}