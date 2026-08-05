package br.com.nfcid.nfc

import android.nfc.tech.IsoDep

/**
 * Envia comandos de aplicação (APDUs) para cartões que falam ISO 14443-4
 * (ISO-DEP) para refinar a identificação: DESFire, cartão de pagamento
 * EMV contactless e Calypso (transporte). Nenhum comando escreve nada
 * no cartão nem tenta autenticação com chaves — só perguntas de leitura
 * pública de identificação.
 */
object IsoDepProbe {

    data class Result(
        val refinedGuess: String?,
        val fields: List<CardField>,
        val notes: List<String>,
    )

    // SELECT por nome (ISO 7816-4): 00 A4 04 00 Lc <AID> 00
    private fun selectAid(aid: ByteArray): ByteArray {
        val out = ByteArray(6 + aid.size)
        out[0] = 0x00
        out[1] = 0xA4.toByte()
        out[2] = 0x04
        out[3] = 0x00
        out[4] = aid.size.toByte()
        System.arraycopy(aid, 0, out, 5, aid.size)
        out[out.size - 1] = 0x00 // Le
        return out
    }

    private fun isOk(resp: ByteArray): Boolean =
        resp.size >= 2 &&
            (resp[resp.size - 2].toInt() and 0xFF) == 0x90 &&
            (resp[resp.size - 1].toInt() and 0xFF) == 0x00

    fun probe(isoDep: IsoDep): Result {
        val fields = mutableListOf<CardField>()
        val notes = mutableListOf<String>()
        var refined: String? = null

        try {
            if (!isoDep.isConnected) isoDep.connect()
            isoDep.timeout = 3000

            // ATS / bytes históricos (identidade do cartão ISO-DEP).
            isoDep.historicalBytes?.let {
                if (it.isNotEmpty()) fields.add(CardField("Bytes históricos (ATS)", HexUtils.toHexSpaced(it)))
            }
            isoDep.hiLayerResponse?.let {
                if (it.isNotEmpty()) fields.add(CardField("Resposta ISO 14443-B (ATTRIB)", HexUtils.toHexSpaced(it)))
            }

            // 1) DESFire GetVersion (APDU envelopado: 90 60 00 00 00).
            val desfire = tryDesfireVersion(isoDep)
            if (desfire != null) {
                refined = desfire.first
                fields.addAll(desfire.second)
            }

            // 2) Pagamento EMV contactless (PPSE "2PAY.SYS.DDF01").
            if (refined == null) {
                val ppse = HexUtils.fromHex("325041592E5359532E4444463031")
                val resp = safeTransceive(isoDep, selectAid(ppse))
                if (resp != null && isOk(resp)) {
                    refined = "Cartão de pagamento EMV contactless (Visa/Mastercard/Elo). " +
                        "NÃO é um crachá de acesso."
                    notes.add(
                        "Este cartão respondeu ao seletor de pagamento (PPSE). " +
                            "É um cartão bancário/crédito por aproximação, não um crachá de empresa.",
                    )
                }
            }

            // 3) Calypso (transporte público). SELECT AID "1TIC.ICA".
            run {
                val calypso = HexUtils.fromHex("315449432E494341")
                val resp = safeTransceive(isoDep, selectAid(calypso))
                if (resp != null && isOk(resp)) {
                    val g = "Cartão Calypso (transporte público)"
                    refined = if (refined == null) g else "$refined; também responde a Calypso"
                    notes.add("Respondeu ao aplicativo Calypso — típico de bilhete de transporte.")
                }
            }
        } catch (e: Exception) {
            notes.add("Não foi possível concluir a sondagem ISO-DEP: ${e.message ?: "erro de comunicação"}.")
        } finally {
            runCatching { isoDep.close() }
        }

        return Result(refined, fields, notes)
    }

    /**
     * GetVersion do DESFire em três frames (APDU envelopado 0x90..).
     * Retorna descrição + campos, ou null se não for DESFire.
     */
    private fun tryDesfireVersion(isoDep: IsoDep): Pair<String, List<CardField>>? {
        val fields = mutableListOf<CardField>()
        val getVersion = HexUtils.fromHex("90600000 00".replace(" ", ""))
        val more = HexUtils.fromHex("90AF000000")

        val r1 = safeTransceive(isoDep, getVersion) ?: return null
        // Resposta esperada: 7 bytes de HW + SW 91 AF.
        if (r1.size < 9) return null
        val sw1a = r1[r1.size - 2].toInt() and 0xFF
        val sw1b = r1[r1.size - 1].toInt() and 0xFF
        if (!(sw1a == 0x91 && (sw1b == 0xAF || sw1b == 0x00))) return null

        val hw = r1.copyOfRange(0, r1.size - 2)
        val descricao = CardSignatures.describeDesfireHardware(hw) ?: "MIFARE DESFire"
        fields.add(CardField("DESFire — hardware", descricao))
        fields.add(CardField("DESFire — bytes de versão (HW)", HexUtils.toHexSpaced(hw)))

        // Frame 2 (software info).
        val r2 = safeTransceive(isoDep, more)
        if (r2 != null && r2.size >= 9) {
            val sw = (r2[r2.size - 2].toInt() and 0xFF) to (r2[r2.size - 1].toInt() and 0xFF)
            val swInfo = r2.copyOfRange(0, r2.size - 2)
            fields.add(CardField("DESFire — versão de software", HexUtils.toHexSpaced(swInfo)))
            // Frame 3 (produção / UID de 7 bytes).
            if (sw.first == 0x91 && sw.second == 0xAF) {
                val r3 = safeTransceive(isoDep, more)
                if (r3 != null && r3.size >= 2) {
                    val prod = r3.copyOfRange(0, r3.size - 2)
                    fields.add(CardField("DESFire — dados de produção", HexUtils.toHexSpaced(prod)))
                }
            }
        }
        return descricao to fields
    }

    private fun safeTransceive(isoDep: IsoDep, cmd: ByteArray): ByteArray? =
        try {
            isoDep.transceive(cmd)
        } catch (e: Exception) {
            null
        }
}
