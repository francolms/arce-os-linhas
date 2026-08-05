package br.com.nfcid.nfc

import android.nfc.Tag
import android.nfc.tech.IsoDep
import android.nfc.tech.MifareClassic
import android.nfc.tech.MifareUltralight
import android.nfc.tech.Ndef
import android.nfc.tech.NfcA
import android.nfc.tech.NfcB
import android.nfc.tech.NfcF
import android.nfc.tech.NfcV

/**
 * Coração do app: recebe a [Tag] entregue pelo Android e produz uma
 * [CardIdentification] com o melhor palpite de tipo de cartão e todos os
 * dados técnicos coletados. Só faz leituras de identificação — não escreve
 * e não tenta autenticar com chaves.
 */
object CardAnalyzer {

    fun analyze(tag: Tag): CardIdentification {
        val techs = tag.techList
        val sections = mutableListOf<CardSection>()
        val notes = mutableListOf<String>()
        var bestGuess: String? = null
        var confidence = CardIdentification.Confidence.BAIXA

        // ---- Identidade básica (UID + tecnologias) ----
        val uid = tag.id ?: ByteArray(0)
        val basic = mutableListOf(
            CardField("UID", if (uid.isEmpty()) "(indisponível)" else HexUtils.toHexSpaced(uid)),
            CardField("Tamanho do UID", "${uid.size} bytes"),
        )
        CardSignatures.manufacturerFromUid(uid)?.let {
            basic.add(CardField("Fabricante do chip (pelo UID)", it))
        }
        if (uid.size == 4) {
            basic.add(CardField("Observação sobre o UID", "UID de 4 bytes pode ser fixo ou aleatório"))
        }
        basic.add(CardField("Tecnologias NFC detectadas", techs.joinToString("\n") { simplifyTech(it) }))
        sections.add(CardSection("Identificação básica", basic))

        // ---- ISO 14443-A (NfcA): ATQA + SAK ----
        if (techs.contains(NfcA::class.java.name)) {
            try {
                val nfcA = NfcA.get(tag)
                val atqaBytes = nfcA.atqa
                val atqaInt = if (atqaBytes.size >= 2) {
                    (atqaBytes[0].toInt() and 0xFF) or ((atqaBytes[1].toInt() and 0xFF) shl 8)
                } else {
                    -1
                }
                val sak = nfcA.sak.toInt() and 0xFFFF
                val fields = mutableListOf(
                    CardField("ATQA", HexUtils.toHexSpaced(atqaBytes)),
                    CardField("SAK", "0x%02X".format(sak)),
                )
                sections.add(CardSection("ISO 14443-A", fields))

                CardSignatures.guessFromSakAtqa(sak and 0xFF, atqaInt)?.let {
                    bestGuess = it
                    confidence = CardIdentification.Confidence.MEDIA
                }
            } catch (e: Exception) {
                notes.add("Falha ao ler parâmetros ISO 14443-A: ${e.message ?: "erro"}.")
            }
        }

        // ---- MIFARE Classic ----
        if (techs.contains(MifareClassic::class.java.name)) {
            try {
                val mc = MifareClassic.get(tag)
                val tipo = when (mc.type) {
                    MifareClassic.TYPE_CLASSIC -> "Classic"
                    MifareClassic.TYPE_PLUS -> "Plus"
                    MifareClassic.TYPE_PRO -> "Pro"
                    else -> "desconhecido"
                }
                sections.add(
                    CardSection(
                        "MIFARE Classic",
                        listOf(
                            CardField("Tipo", tipo),
                            CardField("Tamanho", "${mc.size} bytes"),
                            CardField("Setores", mc.sectorCount.toString()),
                            CardField("Blocos", mc.blockCount.toString()),
                        ),
                    ),
                )
                bestGuess = "MIFARE Classic $tipo — ${mc.size} bytes"
                confidence = CardIdentification.Confidence.ALTA
                notes.add(
                    "Cartões MIFARE Classic normalmente são identificados pela leitora apenas " +
                        "pelo UID. O celular Android NÃO consegue emular um UID arbitrário, então " +
                        "não é possível fazer o celular passar como este crachá.",
                )
            } catch (e: Exception) {
                notes.add("Falha ao consultar MIFARE Classic: ${e.message ?: "erro"}.")
            }
        }

        // ---- MIFARE Ultralight / NTAG ----
        if (techs.contains(MifareUltralight::class.java.name)) {
            try {
                val mu = MifareUltralight.get(tag)
                val tipo = when (mu.type) {
                    MifareUltralight.TYPE_ULTRALIGHT -> "Ultralight (chip original)"
                    MifareUltralight.TYPE_ULTRALIGHT_C -> "Ultralight C (com 3DES)"
                    else -> "Ultralight / NTAG (variante)"
                }
                sections.add(CardSection("MIFARE Ultralight / NTAG", listOf(CardField("Tipo", tipo))))
                if (bestGuess == null || confidence == CardIdentification.Confidence.MEDIA) {
                    bestGuess = "MIFARE $tipo"
                    confidence = CardIdentification.Confidence.ALTA
                }
            } catch (e: Exception) {
                notes.add("Falha ao consultar Ultralight/NTAG: ${e.message ?: "erro"}.")
            }
        }

        // ---- ISO 14443-B (NfcB): comum em Calypso e documentos ----
        if (techs.contains(NfcB::class.java.name)) {
            try {
                val nfcB = NfcB.get(tag)
                val fields = mutableListOf<CardField>()
                nfcB.applicationData?.let { fields.add(CardField("Dados de aplicação", HexUtils.toHexSpaced(it))) }
                nfcB.protocolInfo?.let { fields.add(CardField("Info de protocolo", HexUtils.toHexSpaced(it))) }
                sections.add(CardSection("ISO 14443-B", fields))
                if (bestGuess == null) {
                    bestGuess = "Cartão ISO 14443-B (pode ser Calypso/transporte ou documento)"
                    confidence = CardIdentification.Confidence.BAIXA
                }
            } catch (e: Exception) {
                notes.add("Falha ao ler ISO 14443-B: ${e.message ?: "erro"}.")
            }
        }

        // ---- FeliCa (NfcF) ----
        if (techs.contains(NfcF::class.java.name)) {
            try {
                val nfcF = NfcF.get(tag)
                sections.add(
                    CardSection(
                        "FeliCa (JIS X 6319-4)",
                        listOf(
                            CardField("Código do sistema", HexUtils.toHexSpaced(nfcF.systemCode)),
                            CardField("Fabricante (PMm)", HexUtils.toHexSpaced(nfcF.manufacturer)),
                        ),
                    ),
                )
                bestGuess = "Cartão FeliCa (padrão japonês; ex.: Suica, Edy)"
                confidence = CardIdentification.Confidence.ALTA
            } catch (e: Exception) {
                notes.add("Falha ao ler FeliCa: ${e.message ?: "erro"}.")
            }
        }

        // ---- ISO 15693 (NfcV): cartões de vizinhança ----
        if (techs.contains(NfcV::class.java.name)) {
            try {
                val nfcV = NfcV.get(tag)
                sections.add(
                    CardSection(
                        "ISO 15693 (NfcV)",
                        listOf(
                            CardField("DSFID", "0x%02X".format(nfcV.dsfId.toInt() and 0xFF)),
                            CardField("Flags de resposta", "0x%02X".format(nfcV.responseFlags.toInt() and 0xFF)),
                        ),
                    ),
                )
                if (bestGuess == null) {
                    bestGuess = "Cartão ISO 15693 (vizinhança) — comum em controle de estoque/acesso"
                    confidence = CardIdentification.Confidence.MEDIA
                }
            } catch (e: Exception) {
                notes.add("Falha ao ler ISO 15693: ${e.message ?: "erro"}.")
            }
        }

        // ---- NDEF (dados regraváveis padronizados) ----
        if (techs.contains(Ndef::class.java.name)) {
            try {
                val ndef = Ndef.get(tag)
                val fields = mutableListOf(
                    CardField("Tipo NDEF", ndef.type ?: "(desconhecido)"),
                    CardField("Capacidade", "${ndef.maxSize} bytes"),
                    CardField("Gravável", if (ndef.isWritable) "sim" else "não"),
                )
                sections.add(CardSection("NDEF", fields))
            } catch (e: Exception) {
                notes.add("Falha ao ler NDEF: ${e.message ?: "erro"}.")
            }
        }

        // ---- ISO-DEP: sondagem por comandos de aplicação ----
        if (techs.contains(IsoDep::class.java.name)) {
            val result = IsoDepProbe.probe(IsoDep.get(tag))
            if (result.fields.isNotEmpty()) {
                sections.add(CardSection("ISO-DEP (comandos de aplicação)", result.fields))
            }
            notes.addAll(result.notes)
            result.refinedGuess?.let {
                bestGuess = it
                confidence = CardIdentification.Confidence.ALTA
            }
        }

        // ---- Observação geral sobre crachás e emulação ----
        addAccessCardNote(techs, notes)

        return CardIdentification(
            bestGuess = bestGuess ?: "Cartão NFC não reconhecido em detalhe (veja os dados técnicos abaixo)",
            confidence = if (bestGuess == null) CardIdentification.Confidence.BAIXA else confidence,
            sections = sections,
            notes = notes,
        )
    }

    private fun addAccessCardNote(techs: Array<String>, notes: MutableList<String>) {
        val temIsoDep = techs.contains(IsoDep::class.java.name)
        if (!temIsoDep) {
            notes.add(
                "Sobre usar o celular no lugar do crachá: a maioria das leitoras de acesso confere " +
                    "o UID do cartão. O Android não permite escolher o UID que o celular apresenta, " +
                    "então não dá para o celular imitar este crachá. A identificação acima serve para " +
                    "você saber exatamente qual tecnologia sua empresa usa.",
            )
        } else {
            notes.add(
                "Este cartão fala ISO-DEP (comandos de aplicação). Sistemas de acesso mais modernos " +
                    "que usam esse modo costumam exigir autenticação com chaves secretas guardadas no " +
                    "chip, que não podem ser lidas nem copiadas. Consulte o RH/segurança da sua empresa " +
                    "sobre credencial no celular (ex.: HID Mobile Access, Google Wallet corporativo).",
            )
        }
    }

    /** Nome curto e amigável para cada tecnologia da techList. */
    private fun simplifyTech(fqcn: String): String {
        val nome = fqcn.substringAfterLast('.')
        return when (nome) {
            "NfcA" -> "NfcA (ISO 14443-A)"
            "NfcB" -> "NfcB (ISO 14443-B)"
            "NfcF" -> "NfcF (FeliCa)"
            "NfcV" -> "NfcV (ISO 15693)"
            "IsoDep" -> "IsoDep (ISO 14443-4, APDUs)"
            "MifareClassic" -> "MIFARE Classic"
            "MifareUltralight" -> "MIFARE Ultralight / NTAG"
            "Ndef" -> "NDEF"
            "NdefFormatable" -> "NDEF formatável"
            else -> nome
        }
    }
}
