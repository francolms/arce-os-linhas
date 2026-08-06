package br.com.nfcid

import android.nfc.NfcAdapter
import android.nfc.Tag
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import br.com.nfcid.nfc.CardAnalyzer
import br.com.nfcid.ui.CardScreen
import br.com.nfcid.ui.ScreenState
import br.com.nfcid.ui.theme.IdentificadorNfcTheme

/**
 * Tela única. Usa o "reader mode" do Android — a forma mais confiável de
 * ler qualquer cartão sem que o sistema tente interpretá-lo como NDEF ou
 * abra outro app. Quando um cartão é aproximado, [onTagDiscovered] roda em
 * uma thread de fundo, analisamos e publicamos o resultado na UI.
 */
class MainActivity : ComponentActivity(), NfcAdapter.ReaderCallback {

    private var nfcAdapter: NfcAdapter? = null

    // Estado observável pela UI Compose.
    private var screenState by mutableStateOf<ScreenState>(ScreenState.WaitingTap)
    private var nfcEnabled by mutableStateOf(false)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        nfcAdapter = NfcAdapter.getDefaultAdapter(this)

        setContent {
            IdentificadorNfcTheme {
                CardScreen(
                    nfcEnabled = nfcEnabled,
                    state = screenState,
                    onLimpar = { screenState = ScreenState.WaitingTap },
                )
            }
        }
    }

    override fun onResume() {
        super.onResume()
        val adapter = nfcAdapter
        nfcEnabled = adapter != null && adapter.isEnabled
        if (adapter != null && adapter.isEnabled) {
            val flags = NfcAdapter.FLAG_READER_NFC_A or
                NfcAdapter.FLAG_READER_NFC_B or
                NfcAdapter.FLAG_READER_NFC_F or
                NfcAdapter.FLAG_READER_NFC_V or
                NfcAdapter.FLAG_READER_SKIP_NDEF_CHECK
            adapter.enableReaderMode(this, this, flags, null)
        }
    }

    override fun onPause() {
        super.onPause()
        nfcAdapter?.disableReaderMode(this)
    }

    /** Chamado em thread de fundo quando um cartão é detectado. */
    override fun onTagDiscovered(tag: Tag) {
        val result = try {
            CardAnalyzer.analyze(tag)
        } catch (e: Exception) {
            runOnUiThread {
                screenState = ScreenState.Error(
                    "Erro ao analisar o cartão: ${e.message ?: "desconhecido"}. " +
                        "Tente aproximar de novo, mais firme.",
                )
            }
            return
        }
        runOnUiThread { screenState = ScreenState.Done(result) }
    }
}
