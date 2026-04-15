Scriptname F4RP_NativeBridge native Hidden

Bool Function SubmitChat(
	Int aiRequestId,
	String asPersonaId,
	String asSessionId,
	String asPlayerText,
	String asPlayerName,
	String asLocation,
	Bool abSpeak = True
) Global Native

Int Function PopCompletedRequestId() Global Native
Bool Function WasRequestSuccessful(Int aiRequestId) Global Native
String Function GetReplyText(Int aiRequestId) Global Native
String Function GetSessionId(Int aiRequestId) Global Native
String Function GetAudioFilePath(Int aiRequestId) Global Native
String Function GetWarning(Int aiRequestId) Global Native
String Function GetError(Int aiRequestId) Global Native
Function ReleaseResult(Int aiRequestId) Global Native
Int Function GetQueueDepth() Global Native
