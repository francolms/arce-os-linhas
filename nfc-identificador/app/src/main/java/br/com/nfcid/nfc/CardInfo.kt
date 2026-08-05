package br.com.nfcid.nfc

/** Um par rótulo/valor exibido na tela de resultado. */
data class CardField(
    val label: String,
    val value: String,
)

/** Uma seção da tela de resultado (título + linhas). */
data class CardSection(
    val title: String,
    val fields: List<CardField>,
)

/**
 * Resultado completo da análise de um cartão aproximado.
 *
 * [bestGuess] é a identificação mais provável em uma frase.
 * [confidence] indica o quão certa é essa identificação.
 * [sections] traz todos os dados técnicos coletados.
 * [notes] traz observações/alertas em linguagem simples.
 */
data class CardIdentification(
    val bestGuess: String,
    val confidence: Confidence,
    val sections: List<CardSection>,
    val notes: List<String>,
) {
    enum class Confidence(val rotulo: String) {
        ALTA("Alta"),
        MEDIA("Média"),
        BAIXA("Baixa"),
    }
}
