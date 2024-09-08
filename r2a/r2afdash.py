# -*- coding: utf-8 -*-
"""
@author: Arthur G. Souza (arthur.souza@aluno.unb.br) 07/09/2024

@description: PyDash Project

Uma implementação do algoritmo FDASH

the quality list is obtained with the parameter of handle_xml_response() method and the choice
is made inside of handle_segment_size_request(), before sending the message down.

In this algorithm the quality choice is always the same.
"""

from player.parser import *
from r2a.ir2a import IR2A
import math, time


class R2AFdash(IR2A):

    def __init__(self, id):
        IR2A.__init__(self, id)
        self.parsed_mpd = ''
        self.qi = []
        self.tempoInicial = time.perf_counter()
        self.tempoFinal = time.perf_counter()
        self.buffer = list()
        self.qualidade = list()
        self.T = 1/4 # corresponde a 1/4 do tamanho do segmento de 1s

    def get_buffering_time(self):
        if len(self.buffer) > 0:
            return self.buffer[-1]
        else:
            return 1

    def get_differential_buffering_time(self):
        if len(self.buffer) > 1:
            return self.buffer[-2] - self.buffer[-1]
        else:
            return 0

    def estimativa_throughput(self, output_fuzzy):
        if len(self.qualidade) == 0:
            valor = output_fuzzy*4 + 2
        elif len(self.qualidade) == 1:
            valor =  self.qualidade[0]
            print("valor1: ", valor)
        elif len(self.qualidade) == 2:
            valor = output_fuzzy*(self.qualidade[0]+self.qualidade[1])/2
            print("valor1: ", valor)
        else:
            valor = output_fuzzy*(self.qualidade[-3]+self.qualidade[-2]+self.qualidade[-1])/3
        if valor >= 19:
            return 19
        return round(valor)

    def controlador_fuzzy(self):
        # variaveis linguisticas

        # buffering time
        t_short = 0
        t_close = 0
        t_long = 0

        # differential buffering time
        t_falling = 0
        t_steady = 0
        t_rising = 0

        tempo_buffering_time = self.get_buffering_time()
        tempo_differential_buffering_time = self.get_differential_buffering_time()

        # funcoes de pertinencia (fuzzificacao)

        # fuzzificacao do buffering time
        if tempo_buffering_time < 2 * self.T / 3:
            t_short = 1.0
        elif tempo_buffering_time < self.T:
            t_short = 1 - 1 / (self.T / 3) * (tempo_buffering_time - 2 * self.T / 3)
            t_close = 1 / (self.T / 3) * (tempo_buffering_time - 2 * self.T / 3)
        elif tempo_buffering_time < 4 * self.T:
            t_close = 1 - 1 / (3 * self.T) * (tempo_buffering_time - self.T)
            t_long = 1 / (3 * self.T) * (tempo_buffering_time - self.T)
        else:
            t_long = 1

        # fuzzificacao do differntial buffering time
        if tempo_differential_buffering_time < -2 * self.T / 3:
            t_falling = 1
        elif tempo_differential_buffering_time < 0:
            t_falling = 1 - 1 / (2 * self.T / 3) * (tempo_differential_buffering_time + 2 * self.T / 3)
            t_steady = 1 / (2 * self.T / 3) * (tempo_differential_buffering_time + 2 * self.T / 3)
        elif tempo_differential_buffering_time < 4 * self.T:
            t_steady = 1 - 1 / (4 * self.T) * tempo_differential_buffering_time
            t_rising = 1 / (4 * self.T) * tempo_differential_buffering_time
        else:
            t_rising = 1

        # regras se entao
        r1 = min(t_short, t_falling)
        r2 = min(t_close, t_falling)
        r3 = min(t_long, t_falling)
        r4 = min(t_short, t_steady)
        r5 = min(t_close, t_steady)
        r6 = min(t_long, t_steady)
        r7 = min(t_short, t_rising)
        r8 = min(t_close, t_rising)
        r9 = min(t_long, t_rising)

        p2 = math.sqrt(r9 ** 2)
        p1 = math.sqrt(r6 ** 2 + r8 ** 2)
        z = math.sqrt(r3 ** 2 + r5 ** 2 + r7 ** 2)
        n1 = math.sqrt(r2 ** 2 + r4 ** 2)
        n2 = math.sqrt(r1 ** 2)

        # funcao de defuzzificacao
        output = (n2 * 0.25 + n1 * 0.5 + z * 1 + p1 * 2 + p2 * 4) / (n2 + n1 + z + p1 + p2)

        # definicao de qualidade
        return self.estimativa_throughput(output)

    def handle_xml_request(self, msg):
        self.send_down(msg)

    def handle_xml_response(self, msg):
        # getting qi list
        self.parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = self.parsed_mpd.get_qi()

        self.send_up(msg)

    def handle_segment_size_request(self, msg):
        self.tempoInicial = time.perf_counter()
        # time to define the segment quality choose to make the request
        msg.add_quality_id(self.qi[self.controlador_fuzzy()])
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        self.tempoFinal = time.perf_counter()
        self.buffer.append(self.tempoFinal-self.tempoInicial)
        if(len(self.whiteboard.get_playback_qi()) > 0):
            self.qualidade.append(self.whiteboard.get_playback_qi()[-1][1])
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass
