; Fleet NSIS include: "register in AI tools" installer page + register/unregister hooks.
; CANONICAL COPY (vendored into <repo>\native\windows\ by the build script).
;
; Usage in <repo>\native\windows\hooks.nsh, BEFORE anything else:
;   !define MCP_REG_NAME "onenote-mcp"                 ; key written into the AI client configs
;   !define MCP_REG_EXE  "onenote-mcp-backend.exe"     ; stdio-capable exe under $INSTDIR\resources\
;   !include "mcp-clients.nsh"
; then call from your own hook macros:
;   NSIS_HOOK_POSTINSTALL  -> !insertmacro McpClientsRegister
;   NSIS_HOOK_PREUNINSTALL -> !insertmacro McpClientsUnregister
; The page itself needs the patched Tauri template (scripts/patch-nsis-template.ps1), which
; expands the NSIS_HOOK_PAGES macro defined below just before the "Installation" page.
;
; Behaviour: the page appears only if at least one supported AI client is detected; its
; checkbox is ON by default. Silent (/S) and passive (/P) installs register by default;
; pass /NOMCP to skip. The work is done by resources\install-mcp-clients.ps1.

!include nsDialogs.nsh
!include LogicLib.nsh

Var McpChk
Var McpRegState
Var McpDetected

!macro NSIS_HOOK_PAGES
  Page custom McpClientsPage McpClientsLeave

  Function McpClientsPage
    ${If} $PassiveMode = 1
      Abort
    ${EndIf}
    StrCpy $McpDetected ""
    IfFileExists "$APPDATA\Claude\*.*" 0 +2
      StrCpy $McpDetected "$McpDetected$\r$\n  - Claude Desktop"
    IfFileExists "$PROFILE\.cursor\*.*" 0 +2
      StrCpy $McpDetected "$McpDetected$\r$\n  - Cursor"
    IfFileExists "$PROFILE\.gemini\antigravity\*.*" 0 +2
      StrCpy $McpDetected "$McpDetected$\r$\n  - Antigravity"
    IfFileExists "$PROFILE\.codeium\windsurf\*.*" 0 +2
      StrCpy $McpDetected "$McpDetected$\r$\n  - Windsurf"
    IfFileExists "$PROFILE\.config\opencode\*.*" 0 +2
      StrCpy $McpDetected "$McpDetected$\r$\n  - OpenCode"
    ${If} $McpDetected == ""
      Abort
    ${EndIf}
    !insertmacro MUI_HEADER_TEXT "AI tool integration" "Make ${MCP_REG_NAME} available in your AI tools"
    nsDialogs::Create 1018
    Pop $0
    ${NSD_CreateLabel} 0 0 100% 72u "AI tools found on this computer:$McpDetected"
    Pop $0
    ${NSD_CreateCheckbox} 0 80u 100% 12u "Register ${MCP_REG_NAME} in these tools (recommended)"
    Pop $McpChk
    ${NSD_Check} $McpChk
    nsDialogs::Show
  FunctionEnd

  Function McpClientsLeave
    ${NSD_GetState} $McpChk $McpRegState
  FunctionEnd
!macroend

!macro McpClientsRegister
  ClearErrors
  ${GetOptions} $CMDLINE "/NOMCP" $R0
  ${If} ${Errors}
  ${AndIf} $McpRegState != "0"
    DetailPrint "Registering ${MCP_REG_NAME} in detected AI tools..."
    nsExec::ExecToLog 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\resources\install-mcp-clients.ps1" -Name "${MCP_REG_NAME}" -Command "$INSTDIR\resources\${MCP_REG_EXE}" -EnvPairs MCP_TRANSPORT=stdio'
    Pop $R0
  ${EndIf}
!macroend

!macro McpClientsUnregister
  DetailPrint "Removing ${MCP_REG_NAME} from AI tool configs..."
  nsExec::ExecToLog 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$INSTDIR\resources\install-mcp-clients.ps1" -Name "${MCP_REG_NAME}" -Uninstall'
  Pop $R0
!macroend
