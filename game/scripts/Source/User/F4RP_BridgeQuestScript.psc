Scriptname F4RP_BridgeQuestScript extends Quest

Actor Property CurrentSpeaker Auto
String Property ActivePersonaId = "steve-jobs" Auto
String Property ActiveSessionId = "" Auto Hidden
Bool Property ConversationOpen = False Auto Hidden
Bool Property DebugMode = True Auto
Int Property LastRequestId = 0 Auto Hidden
Int Property TextInputMode = 1 Auto ; 0 = Scaleform menu, 1 = external overlay (default)
Float Property PollIntervalSeconds = 0.35 Auto
Int Property MaxResultsPerUpdate = 2 Auto
Bool Property SpeakReplies = True Auto

Function DebugNotify(String asMessage)
	If DebugMode
		Debug.Trace("F4RP: " + asMessage)
		Debug.Notification("F4RP: " + asMessage)
	EndIf
EndFunction

Function SetActivePersona(String asPersonaId)
	If asPersonaId == ""
		DebugNotify("Ignored empty persona id")
		Return
	EndIf

	ActivePersonaId = asPersonaId
	DebugNotify("Active persona set to " + ActivePersonaId)
EndFunction

Function StartConversation(Actor akSpeaker, String asPersonaId)
	CurrentSpeaker = akSpeaker
	If asPersonaId != ""
		ActivePersonaId = asPersonaId
	EndIf

	ActiveSessionId = ""
	ConversationOpen = True
	RegisterForSingleUpdate(PollIntervalSeconds)
	DebugNotify("typed dialogue requested for " + ActivePersonaId)
	OpenTypedInputUI()
EndFunction

Function OpenTypedInputUI()
	If TextInputMode == 0
		OpenScaleformTextInput()
	Else
		OpenExternalOverlayTextInput()
	EndIf
EndFunction

Function OpenScaleformTextInput()
	DebugNotify("Scaleform typed menu route selected (not implemented in source stub)")
EndFunction

Function OpenExternalOverlayTextInput()
	Bool opened = NativeBridgeOpenExternalOverlay(ActivePersonaId, ActiveSessionId)
	If opened
		DebugNotify("External overlay route selected; waiting for typed input")
	Else
		DebugNotify("External overlay route selected, but bridge overlay hook is unavailable")
	EndIf
EndFunction

Int Function SubmitTypedTextFromUI(String asPlayerText, String asPlayerName = "Sole Survivor", String asLocation = "The Commonwealth")
	Int requestId = SubmitPlayerText(asPlayerText, asPlayerName, asLocation)
	If requestId > 0
		DebugNotify("UI handed off typed text to bridge request " + requestId)
	EndIf
	Return requestId
EndFunction

Int Function SubmitPlayerText(String asPlayerText, String asPlayerName = "Sole Survivor", String asLocation = "The Commonwealth")
	If !ConversationOpen
		DebugNotify("Submit ignored because conversation is closed")
		Return -1
	EndIf

	If asPlayerText == ""
		DebugNotify("Submit ignored because text was empty")
		Return -1
	EndIf

	LastRequestId += 1
	Int requestId = LastRequestId
	Bool accepted = F4RP_NativeBridge.SubmitChat(
		requestId,
		ActivePersonaId,
		ActiveSessionId,
		asPlayerText,
		asPlayerName,
		asLocation,
		SpeakReplies
	)
	If !accepted
		DebugNotify("Native bridge is unavailable. Request " + requestId + " was not sent.")
	EndIf

	Return requestId
EndFunction

Bool Function NativeBridgeOpenExternalOverlay(String asPersonaId, String asSessionId)
	; Source-only stub.
	; Native F4SE bridge should open or focus the desktop overlay and pass persona/session context.
	Debug.Trace("F4RP: NativeBridgeOpenExternalOverlay stub invoked for persona " + asPersonaId)
	Return False
EndFunction

Function PumpNativeBridgeResults()
	Int processed = 0
	While processed < MaxResultsPerUpdate
		Int requestId = F4RP_NativeBridge.PopCompletedRequestId()
		If requestId < 0
			Return
		EndIf

		Bool success = F4RP_NativeBridge.WasRequestSuccessful(requestId)
		If success
			ReceiveGeneratedReply(
				requestId,
				F4RP_NativeBridge.GetReplyText(requestId),
				F4RP_NativeBridge.GetSessionId(requestId),
				F4RP_NativeBridge.GetAudioFilePath(requestId),
				F4RP_NativeBridge.GetWarning(requestId)
			)
		Else
			ReceiveBridgeError(requestId, F4RP_NativeBridge.GetError(requestId))
		EndIf

		F4RP_NativeBridge.ReleaseResult(requestId)
		processed += 1
	EndWhile
EndFunction

Event OnUpdate()
	If !ConversationOpen
		Return
	EndIf

	PumpNativeBridgeResults()
	RegisterForSingleUpdate(PollIntervalSeconds)
EndEvent

Function ReceiveGeneratedReply(
	Int aiRequestId,
	String asReplyText,
	String asSessionId = "",
	String asAudioFilePath = "",
	String asWarning = ""
)
	If !ConversationOpen
		Return
	EndIf

	If asSessionId != ""
		ActiveSessionId = asSessionId
	EndIf

	Debug.Trace("F4RP reply [" + aiRequestId + "]: " + asReplyText)
	If asWarning != ""
		Debug.Trace("F4RP warning [" + aiRequestId + "]: " + asWarning)
	EndIf

	Debug.Notification(asReplyText)

	; Build target:
	; - Push subtitle text into custom menu.
	; - Trigger talk idle on CurrentSpeaker.
	; - Route asAudioFilePath through sound descriptor or native playback.
EndFunction

Function ReceiveBridgeError(Int aiRequestId, String asError)
	DebugNotify("Bridge error for request " + aiRequestId + ": " + asError)
EndFunction

Function CloseConversation()
	UnregisterForUpdate()
	If TextInputMode == 1
		NativeBridgeCloseExternalOverlay()
	EndIf
	ConversationOpen = False
	CurrentSpeaker = None
	ActiveSessionId = ""
EndFunction

Function NativeBridgeCloseExternalOverlay()
	; Source-only stub.
	Debug.Trace("F4RP: NativeBridgeCloseExternalOverlay stub invoked.")
EndFunction
