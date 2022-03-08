# -*- coding: utf-8 -*-

import os
import logging
import subprocess


class CheckDigit(object):
    """ Modulo 11"""
    _MODULO_11 = {
        "BASE": 11,
        "FACTOR": 2,
        "RETORNO11": 0,
        "RETORNO10": 1,
        "PESO": 2,
        "MAX_WEIGHT": 7
    }

    @classmethod
    def _eval_mod11(cls, modulo):
        if modulo == cls._MODULO_11["BASE"]:
            return cls._MODULO_11["RETORNO11"]
        elif modulo == cls._MODULO_11["BASE"] - 1:
            return cls._MODULO_11["RETORNO10"]
        else:
            return modulo

    @classmethod
    def compute_mod11(cls, dato):
        """
        Calculo mod 11
        return int
        """
        total = 0
        weight = cls._MODULO_11["PESO"]

        for item in reversed(dato):
            total += int(item) * weight
            weight += 1
            if weight > cls._MODULO_11["MAX_WEIGHT"]:
                weight = cls._MODULO_11["PESO"]
        mod = 11 - total % cls._MODULO_11["BASE"]

        mod = cls._eval_mod11(mod)
        return mod


class Xades(object):

    def sign(self, path_xml_document, archivo_xml, path_out_signed, pk12, pk12_pass):
        """
        Metodo que aplica la firma digital al XML
        TODO: Revisar return
        se codifica xml, command lanza java -jar pathjar xmlcodificado file_pk12 password
        ejecuta con subprocess.check_output
        """
        #xml_str = xml_document.encode("utf-8")
        JAR_PATH = "firma/firmaXadesBes.jar"
        JAVA_CMD = "java"
        firma_path = os.path.join(os.path.dirname(__file__), JAR_PATH)
        # path al .jar
        # print("ya codificada  ", base64.b64encode(bytes(file_pk12, "utf-8")))
        command = [
            JAVA_CMD,
            "-jar",
            "-XX:MaxHeapSize=512m",
            firma_path,
            path_xml_document,
            archivo_xml,
            path_out_signed,
            str(pk12),
            str(pk12_pass)
        ]
        # prueba la ejecucion del comando

        try:
            logging.info("Probando comando de firma digital")
            subprocess.check_output(command,stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            returncode = e.returncode
            output = e.output
            logging.error("Llamada a proceso JAVA codigo: %s" % returncode)
            logging.error("Error: %s" % output)
        # abre el subproceso para ser ejecutado en segundo plano
        p = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        # ejecuta el comando  y comunica resultado a la pantalla
        res = p.communicate()
        return res[0]
