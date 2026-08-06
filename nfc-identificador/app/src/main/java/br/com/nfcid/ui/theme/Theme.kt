package br.com.nfcid.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val Azul = Color(0xFF0D47A1)
private val AzulClaro = Color(0xFF5472D3)

private val LightColors = lightColorScheme(
    primary = Azul,
    secondary = AzulClaro,
)

private val DarkColors = darkColorScheme(
    primary = AzulClaro,
    secondary = Azul,
)

@Composable
fun IdentificadorNfcTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    content: @Composable () -> Unit,
) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        content = content,
    )
}
