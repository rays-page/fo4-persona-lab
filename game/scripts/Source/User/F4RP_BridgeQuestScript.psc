Scriptname F4RP_BridgeQuestScript extends Quest

Actor Property CurrentSpeaker Auto
String Property ActivePersonaId Auto
Bool Property ConversationOpen Auto

Function StartConversation(Actor akSpeaker, String asPersonaId)
	CurrentSpeaker = akSpeaker
	ActivePersonaId = asPersonaId
	ConversationOpen = True
	Debug.Notification("F4RP: typed dialogue bridge requested")
	; Final build target:
	; 1. Open a custom Scaleform menu or external overlay.
	; 2. Pass ActivePersonaId, player name, and location to the bridge.
	; 3. Receive response text and optional audio path from native code.
EndFunction

Function ReceiveGeneratedReply(String asReplyText, String asAudioPath = "")
	If !ConversationOpen
		Return
	EndIf

	Debug.Trace("F4RP reply: " + asReplyText)
	Debug.Notification(asReplyText)

	; Final build target:
	; - Push subtitle text into the custom menu.
	; - Play a talk idle on CurrentSpeaker.
	; - Route generated audio through a sound descriptor or native playback bridge.
EndFunction

Function CloseConversation()
	ConversationOpen = False
	CurrentSpeaker = None
	ActivePersonaId = ""
EndFunction
