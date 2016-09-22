# -*- coding: utf-8 -*-

import telegram
from telegram.ext import Updater
from telegram.ext import MessageHandler, Filters

from datetime import datetime
import configparser
import threading, inspect, shlex
try:
    import Queue
except ImportError:
    import queue as Queue

import os
import sys
sys.path.append(os.getcwd() + '/yowsup')

from yowsup.stacks                                     import YowStackBuilder
from yowsup.layers                                     import YowLayerEvent
from yowsup.layers.network                             import YowNetworkLayer
from yowsup.layers.interface                           import YowInterfaceLayer, ProtocolEntityCallback
from yowsup.layers.protocol_receipts.protocolentities  import OutgoingReceiptProtocolEntity
from yowsup.layers.protocol_acks.protocolentities      import OutgoingAckProtocolEntity
from yowsup.layers.protocol_messages.protocolentities  import TextMessageProtocolEntity
from yowsup.layers.protocol_presence.protocolentities  import PresenceProtocolEntity
from yowsup.common.tools import Jid

config = configparser.ConfigParser()
config.read('config.ini')

tg_token = config.get('access', 'tg_token')
tg_chat = config.get('access', 'tg_chat')
wa_phone = config.get('access', 'wa_phone')
wa_pass = config.get('access', 'wa_pass')
wa_chat = config.get('access', 'wa_chat')
wa_nickname = config.get('access', 'wa_nickname')
wa_send_queue = Queue.Queue()

class EchoLayer(YowInterfaceLayer):
    def __init__(self):
        super(EchoLayer, self).__init__()

        self.listenQueueThread = threading.Thread(target = self.listenSendQueue)
        self.listenQueueThread.daemon = True
        self.listenQueueThread.start()

    @ProtocolEntityCallback("message")
    def onMessage(self, messageProtocolEntity):
        print "[WA]: chat_id=%s, from=%s, nick=%s, text=%s" % (messageProtocolEntity.getFrom(),
                                                               messageProtocolEntity.getAuthor(),
                                                               messageProtocolEntity.getNotify(),
                                                               messageProtocolEntity.getBody())
        # import ipdb; ipdb.set_trace()
        receipt = OutgoingReceiptProtocolEntity(messageProtocolEntity.getId(), messageProtocolEntity.getFrom(), \
                                                'read', messageProtocolEntity.getParticipant())

        self.toLower(receipt)
        tg_message = "[%s][%s] %s" % (messageProtocolEntity.getFrom(), messageProtocolEntity.getNotify(), messageProtocolEntity.getBody())
        self.getProp('telegram').sendMessage(chat_id=tg_chat, text=tg_message)

    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        ack = OutgoingAckProtocolEntity(entity.getId(), "receipt", entity.getType(), entity.getFrom())
        self.toLower(ack)

    @ProtocolEntityCallback("success")
    def onSuccess(self, entity):
        nickname = self.getProp('wa_nickname')
        if nickname:
            self.toLower(PresenceProtocolEntity(name = nickname))

    def listenSendQueue(self):
        while not self.getStack() or not self.getProp('send_queue'):
            pass
        sendQueue = self.getProp('send_queue')
        while True:
            msg = sendQueue.get(True)
            outgoingMessageProtocolEntity = TextMessageProtocolEntity(msg, to = Jid.normalize(self.getProp('wa_chat')))
            # TextMessageProtocolEntity(content.encode("utf-8") if sys.version_info >= (3,0) else content, to = self.aliasToJid(number))
            self.toLower(outgoingMessageProtocolEntity)


if __name__==  "__main__":
    starte_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tg = telegram.Bot(token=tg_token)

    def tg_message(bot, update):
        print "[TG]: chat_id=%s, text=%s" % (str(update.message.chat_id), update.message.text)
        # import ipdb; ipdb.set_trace()
        wa_send_queue.put(update.message.text)

    def tg_listen():
        tg_updater = Updater(bot=tg)
        echo_handler = MessageHandler([Filters.text], tg_message)
        tg_updater.dispatcher.add_handler(echo_handler)
        tg.sendMessage(chat_id=tg_chat, text="WathsApp bot started at %s" % starte_time)
        tg_updater.start_polling()

    tgThread = threading.Thread(target = tg_listen)
    tgThread.daemon = True
    tgThread.start()

    stackBuilder = YowStackBuilder()

    stack = stackBuilder \
        .pushDefaultLayers(True) \
        .push(EchoLayer) \
        .build()

    stack.setProp('telegram', tg)
    stack.setProp('send_queue', wa_send_queue)
    stack.setProp('wa_chat', wa_chat)
    stack.setProp('wa_nickname', wa_nickname)
    stack.setCredentials((wa_phone, wa_pass))
    stack.broadcastEvent(YowLayerEvent(YowNetworkLayer.EVENT_STATE_CONNECT))
    try:
        print "Start WA loop"
        stack.loop()
    except Exception as e:
        tg.sendMessage(chat_id=tg_chat, text="WathsApp bot stopped at %s. Error: %s" % (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), e.message))
    except:
        tg.sendMessage(chat_id=tg_chat, text="WathsApp bot gracefully stopped at %s" % datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

