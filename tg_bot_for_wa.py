import telegram
from datetime import datetime
import configparser

import os
import sys
sys.path.append(os.getcwd() + '/yowsup')

from yowsup.stacks                                     import YowStackBuilder
from yowsup.layers                                     import YowLayerEvent
from yowsup.layers.network                             import YowNetworkLayer
from yowsup.layers.interface                           import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.protocol_receipts.protocolentities  import OutgoingReceiptProtocolEntity
from yowsup.layers.protocol_acks.protocolentities      import OutgoingAckProtocolEntity

config = configparser.ConfigParser()
config.read('config.ini')

tg_token = config.get('access', 'tg_token')
tg_chat = config.get('access', 'tg_chat')
wa_phone = config.get('access', 'wa_phone')
wa_pass = config.get('access', 'wa_pass')

class EchoLayer(YowInterfaceLayer):
    @ProtocolEntityCallback("message")
    def onMessage(self, messageProtocolEntity):
        receipt = OutgoingReceiptProtocolEntity(messageProtocolEntity.getId(), messageProtocolEntity.getFrom(), \
                                                'read', messageProtocolEntity.getParticipant())

        # outgoingMessageProtocolEntity = TextMessageProtocolEntity(
        #     messageProtocolEntity.getBody(),
        #     to = messageProtocolEntity.getFrom())

        self.toLower(receipt)
        self.getProp('telegram').sendMessage(chat_id=tg_chat, text=messageProtocolEntity.getBody())
        # self.toLower(outgoingMessageProtocolEntity)

    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        ack = OutgoingAckProtocolEntity(entity.getId(), "receipt", entity.getType(), entity.getFrom())
        self.toLower(ack)

if __name__==  "__main__":
    starte_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tg = telegram.Bot(token=tg_token)
    tg.sendMessage(chat_id=tg_chat, text="WathsApp bot started at %s" % starte_time)

    stackBuilder = YowStackBuilder()

    stack = stackBuilder \
        .pushDefaultLayers(True) \
        .push(EchoLayer) \
        .build()

    stack.setProp('telegram', tg)
    stack.setCredentials((wa_phone, wa_pass))
    stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))
    try:
        stack.loop()
    except Exception as e:
        tg.sendMessage(chat_id=tg_chat, text="Launched at %s. Error: %s" % (starte_time, e.message))


