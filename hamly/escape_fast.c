// modified copy of https://github.com/mitsuhiko/markupsafe/blob/master/markupsafe/_speedups.c

#include <Python.h>

#define ESCAPED_CHARS_TABLE_SIZE 63
#define UNICHR(x) (PyUnicode_AS_UNICODE((PyUnicodeObject*)PyUnicode_DecodeASCII(x, strlen(x), NULL)));

#if PY_VERSION_HEX < 0x02050000 && !defined(PY_SSIZE_T_MIN)
typedef int Py_ssize_t;
#define PY_SSIZE_T_MAX INT_MAX
#define PY_SSIZE_T_MIN INT_MIN
#endif


static Py_ssize_t escaped_chars_delta_len[ESCAPED_CHARS_TABLE_SIZE];
static Py_UNICODE *escaped_chars_repl[ESCAPED_CHARS_TABLE_SIZE];

static int
init_constants(void)
{
    escaped_chars_repl['"'] = UNICHR("&#34;");
    escaped_chars_repl['\''] = UNICHR("&#39;");
    escaped_chars_repl['&'] = UNICHR("&amp;");
    escaped_chars_repl['<'] = UNICHR("&lt;");
    escaped_chars_repl['>'] = UNICHR("&gt;");

    memset(escaped_chars_delta_len, 0, sizeof (escaped_chars_delta_len));
    escaped_chars_delta_len['"'] = escaped_chars_delta_len['\''] = \
        escaped_chars_delta_len['&'] = 4;
    escaped_chars_delta_len['<'] = escaped_chars_delta_len['>'] = 3;
    
    return 1;
}

static PyObject*
escape_unicode(PyUnicodeObject *in)
{
    PyUnicodeObject *out;
    Py_UNICODE *inp = PyUnicode_AS_UNICODE(in);
    const Py_UNICODE *inp_end = PyUnicode_AS_UNICODE(in) + PyUnicode_GET_SIZE(in);
    Py_UNICODE *next_escp;
    Py_UNICODE *outp;
    Py_ssize_t delta=0, erepl=0, delta_len=0;

    while (*(inp) || inp < inp_end) {
        if (*inp < ESCAPED_CHARS_TABLE_SIZE) {
            delta += escaped_chars_delta_len[*inp];
            erepl += !!escaped_chars_delta_len[*inp];
        }
        ++inp;
    }

    if (!erepl) {
        Py_INCREF(in);
        return (PyObject*)in;
    }

    out = (PyUnicodeObject*)PyUnicode_FromUnicode(NULL, PyUnicode_GET_SIZE(in) + delta);
    if (!out)
        return NULL;

    outp = PyUnicode_AS_UNICODE(out);
    inp = PyUnicode_AS_UNICODE(in);
    while (erepl-- > 0) {
        next_escp = inp;
        while (next_escp < inp_end) {
            if (*next_escp < ESCAPED_CHARS_TABLE_SIZE &&
                (delta_len = escaped_chars_delta_len[*next_escp])) {
                ++delta_len;
                break;
            }
            ++next_escp;
        }
        
        if (next_escp > inp) {
            Py_UNICODE_COPY(outp, inp, next_escp-inp);
            outp += next_escp - inp;
        }

        Py_UNICODE_COPY(outp, escaped_chars_repl[*next_escp], delta_len);
        outp += delta_len;

        inp = next_escp + 1;
    }
    if (inp < inp_end)
        Py_UNICODE_COPY(outp, inp, PyUnicode_GET_SIZE(in) - (inp - PyUnicode_AS_UNICODE(in)));

    return (PyObject*)out;
}

static PyObject*
soft_unicode(PyObject *self, PyObject *s)
{
    if (!PyUnicode_Check(s))
#if PY_MAJOR_VERSION < 3
        return PyObject_Unicode(s);
#else
        return PyObject_Str(s);
#endif
    Py_INCREF(s);
    return s;
}


static PyObject*
escape(PyObject *self, PyObject *text)
{
    PyObject *s = NULL, *rv = NULL, *html;

    if (PyLong_CheckExact(text) ||
#if PY_MAJOR_VERSION < 3
        PyInt_CheckExact(text) ||
#endif
        PyFloat_CheckExact(text) || PyBool_Check(text) ||
        text == Py_None)
#if PY_MAJOR_VERSION < 3
        return PyObject_Unicode(text);
#else
        return PyObject_Str(text);
#endif

    PyErr_Clear();
    if (!PyUnicode_Check(text)) {
#if PY_MAJOR_VERSION < 3
        PyObject *unicode = PyObject_Unicode(text);
#else
        PyObject *unicode = PyObject_Str(text);
#endif
        if (!unicode)
            return NULL;
        s = escape_unicode((PyUnicodeObject*)unicode);
        Py_DECREF(unicode);
    }
    else
        s = escape_unicode((PyUnicodeObject*)text);

    return s;
}


static PyMethodDef module_methods[] = {
    {"escape", (PyCFunction)escape, METH_O,
     "escape(s) -> str"},
    {"soft_unicode", (PyCFunction)soft_unicode, METH_O,
     "soft_unicode(object) -> string"},
    {NULL, NULL, 0, NULL}
};


#if PY_MAJOR_VERSION < 3

#ifndef PyMODINIT_FUNC
#define PyMODINIT_FUNC void
#endif
PyMODINIT_FUNC
initescape_fast(void)
{
    if (!init_constants())
        return;

    Py_InitModule3("escape_fast", module_methods, "");
}

#else

static struct PyModuleDef module_definition = {
        PyModuleDef_HEAD_INIT,
    "escape_fast",
    NULL,
    -1,
    module_methods,
    NULL,
    NULL,
    NULL,
    NULL
};

PyMODINIT_FUNC
PyInit_escape_fast(void)
{
    if (!init_constants())
        return NULL;

    return PyModule_Create(&module_definition);
}

#endif
