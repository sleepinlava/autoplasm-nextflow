/* Shell quoting only; full runtime resource identity is still pending. */
def mobsuiteQuote(value) {
    return "'" + value.toString().replace("'", "'\"'\"'") + "'"
}
