# Identificador NFC (Android)

App Android que **lê um cartão por aproximação (NFC) e descobre qual é o tipo
do cartão** — MIFARE Classic, Ultralight/NTAG, DESFire (EV1/EV2/EV3), Calypso,
FeliCa, ISO 15693, cartão de pagamento EMV, etc. — mostrando também todos os
dados técnicos de identificação (UID, ATQA, SAK, ATS, versão de hardware...).

Foi feito para responder à pergunta *"que cartão é esse crachá da minha
empresa?"* sem precisar de equipamento especializado.

## Importante: o que este app faz e o que NÃO faz

- ✅ **Identifica** o tipo/tecnologia do cartão e mostra os dados de
  identificação que são de leitura pública.
- ❌ **Não clona** o cartão e **não faz o celular passar como o crachá**. Isso
  é uma limitação real da tecnologia, não do app:
  - Crachás de **125 kHz** (baixa frequência, ex.: HID Prox, EM4100) **nenhum
    celular lê** — o NFC do celular só opera em 13,56 MHz. Se ao aproximar o
    app não detectar nada, é quase certo que o crachá é 125 kHz.
  - A maioria das leitoras de acesso confere apenas o **UID** do cartão, e o
    Android **não permite escolher o UID** que o celular apresenta. Logo, o
    celular não consegue imitar o crachá.
  - Cartões mais novos (DESFire/Plus) autenticam com **chaves secretas dentro
    do chip que não podem ser lidas nem copiadas**.
  - Caminho legítimo para "menos cartões na carteira": credencial no celular
    oferecida pela própria empresa (ex.: HID Mobile Access) ou carteira
    corporativa — pergunte ao RH/segurança.

## Como compilar e instalar

**Pré‑requisitos:** um celular Android com NFC e o
[Android Studio](https://developer.android.com/studio).

1. Abra o Android Studio → **Open** → selecione a pasta `nfc-identificador/`.
   O Android Studio baixa as dependências e gera o Gradle Wrapper
   automaticamente.
2. Conecte o celular por USB com a **depuração USB** ativada
   (Configurações → Opções do desenvolvedor).
3. Clique em **Run ▶**. O app é instalado e aberto no celular.

> Prefere linha de comando? Depois de abrir uma vez no Android Studio (que
> cria o `gradlew`), rode `./gradlew installDebug` com o celular conectado.

## Como usar

1. Ative o **NFC** no celular (Configurações → Conexões → NFC).
2. Abra o app **Identificador NFC**.
3. Encoste o crachá na parte de trás do celular (a antena NFC costuma ficar
   no terço superior). Segure firme por 1–2 segundos.
4. O app mostra o **provável tipo de cartão**, o nível de confiança,
   observações em linguagem simples e todos os dados técnicos.

## Estrutura do código

| Arquivo | Papel |
|---|---|
| `MainActivity.kt` | Ativa o *reader mode* do NFC e mostra a tela. |
| `nfc/CardAnalyzer.kt` | Reúne todos os dados da tag e monta a identificação. |
| `nfc/CardSignatures.kt` | Tabelas SAK/ATQA, fabricante pelo UID, versão DESFire. |
| `nfc/IsoDepProbe.kt` | Comandos de aplicação (DESFire, EMV/PPSE, Calypso). |
| `nfc/CardInfo.kt` | Modelos de dados do resultado. |
| `nfc/HexUtils.kt` | Conversões de bytes/hex. |
| `ui/CardScreen.kt` | Tela Compose com o resultado. |

Toda a análise é **somente leitura de identificação**: o app não escreve no
cartão nem tenta autenticar com chaves.
