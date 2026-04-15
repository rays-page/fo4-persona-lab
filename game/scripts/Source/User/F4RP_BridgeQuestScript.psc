Scriptname F4RP_BridgeQuestScript extends Quest

Actor Property CurrentSpeaker Auto
String Property ActivePersonaId = "steve-jobs" Auto
String Property ActiveSessionId = "" Auto Hidden
Bool Property ConversationOpen = False Auto Hidden
Bool Property DebugMode = True Auto
Int Property LastRequestId = 0 Auto Hidden

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
	DebugNotify("typed dialogue bridge requested for " + ActivePersonaId)
	; Build target:
	; 1. Open custom Scaleform menu or external overlay.
	; 2. Capture player text entry.
	; 3. Call SubmitPlayerText for each turn.
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
	Bool accepted = NativeBridgeSendChat(
		requestId,
		ActivePersonaId,
		ActiveSessionId,
		asPlayerText,
		asPlayerName,
		asLocation
	)
	If !accepted
		DebugNotify("Native bridge is unavailable. Request " + requestId + " was not sent.")
	EndIf

	Return requestId
EndFunction

Bool Function NativeBridgeSendChat(
	Int aiRequestId,
	String asPersonaId,
	String asSessionId,
	String asPlayerText,
	String asPlayerName,
	String asLocation
)
	; Source-only stub.
	; Native F4SE bridge should:
	; - call local service /api/chat,
	; - return response text and optional audio path,
	; - then call ReceiveGeneratedReply or ReceiveBridgeError.
	Debug.Trace("F4RP: NativeBridgeSendChat stub invoked for request " + aiRequestId)
	Return False
EndFunction

Function ReceiveGeneratedReply(
	Int aiRequestId,
	String asReplyText,
	String asSessionId = "",
	String asAudioPath = "",
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
	; - Route asAudioPath through sound descriptor or native playback.
EndFunction

Function ReceiveBridgeError(Int aiRequestId, String asError)
	DebugNotify("Bridge error for request " + aiRequestId + ": " + asError)
EndFunction

Function CloseConversation()
	ConversationOpen = False
	CurrentSpeaker = None
	ActiveSessionId = ""
EndFunction
