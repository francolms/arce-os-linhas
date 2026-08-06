package br.com.nfcid.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import br.com.nfcid.nfc.CardIdentification

/** Estado da tela: aguardando aproximação, lendo, ou com resultado. */
sealed interface ScreenState {
    data object WaitingTap : ScreenState
    data class Error(val message: String) : ScreenState
    data class Done(val result: CardIdentification) : ScreenState
}

@Composable
fun CardScreen(
    nfcEnabled: Boolean,
    state: ScreenState,
    onLimpar: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        Text(
            "Identificador de Cartão NFC",
            fontSize = 22.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary,
        )
        Spacer(Modifier.padding(4.dp))

        if (!nfcEnabled) {
            AvisoCard(
                "NFC desligado",
                "Ative o NFC nas configurações do celular para ler um cartão.",
            )
            return@Column
        }

        when (state) {
            is ScreenState.WaitingTap -> {
                AvisoCard(
                    "Aproxime o cartão",
                    "Encoste o crachá na parte de trás do celular (geralmente no topo). " +
                        "Segure firme por 1–2 segundos.\n\n" +
                        "Se nada acontecer ao encostar, é bem provável que o cartão seja de " +
                        "125 kHz (baixa frequência) — nesse caso NENHUM celular consegue lê-lo.",
                )
            }

            is ScreenState.Error -> {
                AvisoCard("Não deu para ler", state.message)
                Spacer(Modifier.padding(8.dp))
                Button(onClick = onLimpar) { Text("Tentar de novo") }
            }

            is ScreenState.Done -> {
                ResultadoCard(state.result)
                Spacer(Modifier.padding(8.dp))
                Button(onClick = onLimpar) { Text("Ler outro cartão") }
                Spacer(Modifier.padding(24.dp))
            }
        }
    }
}

@Composable
private fun AvisoCard(titulo: String, texto: String) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
    ) {
        Column(Modifier.padding(16.dp)) {
            Text(titulo, fontWeight = FontWeight.Bold, fontSize = 18.sp)
            Spacer(Modifier.padding(4.dp))
            Text(texto, fontSize = 15.sp)
        }
    }
}

@Composable
private fun ResultadoCard(result: CardIdentification) {
    // Cabeçalho: melhor palpite + confiança.
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer),
    ) {
        Column(Modifier.padding(16.dp)) {
            Text("Provável cartão:", fontSize = 13.sp)
            Text(result.bestGuess, fontWeight = FontWeight.Bold, fontSize = 18.sp)
            Spacer(Modifier.padding(2.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("Confiança: ", fontSize = 13.sp)
                Text(
                    result.confidence.rotulo,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.Bold,
                    color = when (result.confidence) {
                        CardIdentification.Confidence.ALTA -> Color(0xFF1B5E20)
                        CardIdentification.Confidence.MEDIA -> Color(0xFFE65100)
                        CardIdentification.Confidence.BAIXA -> Color(0xFFB71C1C)
                    },
                )
            }
        }
    }

    Spacer(Modifier.padding(6.dp))

    // Observações em linguagem simples.
    if (result.notes.isNotEmpty()) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceVariant),
        ) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Observações", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                result.notes.forEach { Text("• $it", fontSize = 14.sp) }
            }
        }
        Spacer(Modifier.padding(6.dp))
    }

    // Dados técnicos por seção.
    result.sections.forEach { secao ->
        Card(modifier = Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp)) {
                Text(
                    secao.title,
                    fontWeight = FontWeight.Bold,
                    fontSize = 16.sp,
                    color = MaterialTheme.colorScheme.primary,
                )
                Spacer(Modifier.padding(2.dp))
                secao.fields.forEach { campo ->
                    Column(Modifier.padding(vertical = 4.dp)) {
                        Text(campo.label, fontSize = 12.sp, fontWeight = FontWeight.Medium)
                        Text(
                            campo.value,
                            fontSize = 14.sp,
                            fontFamily = FontFamily.Monospace,
                        )
                    }
                }
            }
        }
        Spacer(Modifier.padding(4.dp))
    }
}
