package br.com.nfcid.nfc

/** Conversões e formatações de bytes usadas na análise NFC. */
object HexUtils {

    private val HEX = "0123456789ABCDEF".toCharArray()

    /** Bytes -> "0A1B2C" (maiúsculas, sem separador). Nulo/vazio vira "". */
    fun toHex(bytes: ByteArray?): String {
        if (bytes == null || bytes.isEmpty()) return ""
        val sb = StringBuilder(bytes.size * 2)
        for (b in bytes) {
            val v = b.toInt() and 0xFF
            sb.append(HEX[v ushr 4]).append(HEX[v and 0x0F])
        }
        return sb.toString()
    }

    /** Bytes -> "0A 1B 2C" (com espaços), melhor para leitura humana. */
    fun toHexSpaced(bytes: ByteArray?): String {
        if (bytes == null || bytes.isEmpty()) return ""
        val sb = StringBuilder(bytes.size * 3)
        for (b in bytes) {
            val v = b.toInt() and 0xFF
            sb.append(HEX[v ushr 4]).append(HEX[v and 0x0F]).append(' ')
        }
        return sb.toString().trim()
    }

    /** "00A404000E..." -> ByteArray. Ignora espaços. Aceita maiúsc/minúsc. */
    fun fromHex(hex: String): ByteArray {
        val clean = hex.replace(" ", "").replace("\n", "")
        require(clean.length % 2 == 0) { "String hex com tamanho ímpar" }
        val out = ByteArray(clean.length / 2)
        var i = 0
        while (i < clean.length) {
            val hi = Character.digit(clean[i], 16)
            val lo = Character.digit(clean[i + 1], 16)
            require(hi >= 0 && lo >= 0) { "Caractere hex inválido" }
            out[i / 2] = ((hi shl 4) or lo).toByte()
            i += 2
        }
        return out
    }
}
