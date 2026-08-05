package br.com.nfcid.nfc

/**
 * Tabelas de referência para deduzir o modelo do chip a partir das
 * respostas de baixo nível do protocolo ISO 14443-A (ATQA + SAK) e do
 * byte de fabricante do UID.
 *
 * As combinações abaixo são as amplamente documentadas para chips NXP
 * (MIFARE), Infineon e afins. Servem como pista forte, mas a confirmação
 * final vem dos comandos de aplicação (ex.: GetVersion do DESFire).
 */
object CardSignatures {

    /**
     * Palpite de modelo a partir de SAK e ATQA (ISO 14443-A).
     * ATQA vem como 2 bytes little-endian lidos do NfcA; aqui recebemos
     * o valor já montado como inteiro (byte0 | byte1<<8).
     */
    fun guessFromSakAtqa(sak: Int, atqa: Int): String? {
        return when (sak) {
            0x00 -> when (atqa) {
                0x0044 -> "MIFARE Ultralight / Ultralight C / NTAG (ISO 14443-A, sem ISO-DEP)"
                else -> "Chip tipo 2 (Ultralight/NTAG) ou tag NDEF simples"
            }
            0x08 -> "MIFARE Classic 1K (ou compatível 1K)"
            0x09 -> "MIFARE Mini (320 bytes)"
            0x10 -> "MIFARE Plus 2K (nível de segurança 1)"
            0x11 -> "MIFARE Plus 4K (nível de segurança 1)"
            0x18 -> "MIFARE Classic 4K (ou compatível 4K)"
            0x19 -> "MIFARE Classic 2K"
            0x20 -> when (atqa) {
                0x0344 -> "MIFARE DESFire / DESFire EVx ou MIFARE Plus (ISO 14443-4)"
                0x0044 -> "Cartão ISO 14443-4 (JavaCard / DESFire / EMV)"
                else -> "Cartão com ISO 14443-4 (suporta APDUs)"
            }
            0x28 -> "SmartMX com emulação MIFARE Classic 1K (JavaCard)"
            0x38 -> "SmartMX com emulação MIFARE Classic 4K (JavaCard)"
            0x88 -> "Infineon SLE (compatível MIFARE Classic 1K)"
            else -> null
        }
    }

    /** Nome do fabricante pelo primeiro byte do UID (ISO/IEC 7816-6 / registro). */
    fun manufacturerFromUid(uid: ByteArray): String? {
        if (uid.isEmpty()) return null
        return when (uid[0].toInt() and 0xFF) {
            0x04 -> "NXP Semiconductors"
            0x02 -> "STMicroelectronics"
            0x05 -> "Infineon Technologies"
            0x07 -> "Texas Instruments"
            0x08 -> "Fujitsu"
            0x16 -> "EM Microelectronic-Marin"
            0x1D -> "ASK / Paragon (comum em Calypso)"
            0x28 -> "Samsung"
            0x2B -> "Sony (FeliCa)"
            0x35 -> "Sony"
            else -> null
        }
    }

    /**
     * Interpreta os 7 bytes retornados pelo comando GetVersion (0x60) de um
     * cartão MIFARE DESFire, identificando família e tamanho de memória.
     * Recebe o bloco de "hardware information" (7 bytes: vendor, type,
     * subtype, major, minor, storage, protocol).
     */
    fun describeDesfireHardware(hw: ByteArray): String? {
        if (hw.size < 7) return null
        val major = hw[3].toInt() and 0xFF
        val storageCode = hw[5].toInt() and 0xFF

        val familia = when (major) {
            0x00 -> "DESFire (MF3ICD40, original)"
            0x01 -> "DESFire EV1"
            0x12 -> "DESFire EV2"
            0x33 -> "DESFire EV3"
            else -> "DESFire (versão de hardware 0x%02X)".format(major)
        }

        // storageCode: bit0=1 => faixa aproximada; nn>>1 = 2^n bytes.
        val tamanho = when (storageCode) {
            0x16 -> "2 KB"
            0x18 -> "4 KB"
            0x1A -> "8 KB"
            0x1C -> "16 KB"
            0x1E -> "32 KB"
            else -> "código de armazenamento 0x%02X".format(storageCode)
        }
        return "$familia — memória $tamanho"
    }
}
