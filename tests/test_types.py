from nutils.testing import TestCase, parametrize
import nutils.types
import inspect
import pickle
import itertools
import ctypes
import tempfile
import os
import numpy
import weakref
import contextlib
import unittest
import sys


class apply_annotations(TestCase):

    def test_without_annotations(self):
        @nutils.types.apply_annotations
        def f(a, b):
            return a, b
        a, b = f(1, 2)
        self.assertEqual(a, 1)
        self.assertEqual(b, 2)

    def test_pos_or_kw(self):
        @nutils.types.apply_annotations
        def f(a: int, b, c: str):
            return a, b, c
        a, b, c = f(1, 2, 3)
        self.assertEqual(a, 1)
        self.assertEqual(b, 2)
        self.assertEqual(c, '3')

    def test_with_signature(self):
        def f(a):
            return a
        f.__signature__ = inspect.Signature([inspect.Parameter('a', inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=str)])
        f = nutils.types.apply_annotations(f)
        self.assertEqual(f(1), '1')

    def test_posonly(self):
        def f(a):
            return a
        f.__signature__ = inspect.Signature([inspect.Parameter('a', inspect.Parameter.POSITIONAL_ONLY, annotation=str)])
        f = nutils.types.apply_annotations(f)
        self.assertEqual(f(1), '1')

    def test_kwonly(self):
        @nutils.types.apply_annotations
        def f(a: str, *, b: int, c: bool):
            return a, b, c
        self.assertEqual(f(1, b='2', c=3), ('1', 2, True))

    def test_varpos(self):
        @nutils.types.apply_annotations
        def f(a: str, *args):
            return a, args
        self.assertEqual(f(1, 2, 3), ('1', (2, 3)))

    def test_varpos_annotated(self):
        map_str = lambda args: map(str, args)

        @nutils.types.apply_annotations
        def f(a: str, *args: map_str):
            return a, args
        self.assertEqual(f(1, 2, 3), ('1', ('2', '3')))

    def test_varkw(self):
        @nutils.types.apply_annotations
        def f(a: str, **kwargs):
            return a, kwargs
        self.assertEqual(f(1, b=2, c=3), ('1', dict(b=2, c=3)))

    def test_varkw_annotated(self):
        map_str = lambda kwargs: {k: str(v) for k, v in kwargs.items()}

        @nutils.types.apply_annotations
        def f(a: str, **kwargs: map_str):
            return a, kwargs
        self.assertEqual(f(1, b=2, c=3), ('1', dict(b='2', c='3')))

    def test_posonly_varkw(self):
        def f(a, b, **c):
            return a, b, c
        f.__signature__ = inspect.Signature([inspect.Parameter('a', inspect.Parameter.POSITIONAL_ONLY, annotation=str),
                                             inspect.Parameter('b', inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=str, default=None),
                                             inspect.Parameter('c', inspect.Parameter.VAR_KEYWORD)])
        f = nutils.types.apply_annotations(f)
        self.assertEqual(f(1, c=2, d=3), ('1', None, dict(c=2, d=3)))
        self.assertEqual(f(1, None, c=2, d=3), ('1', None, dict(c=2, d=3)))
        self.assertEqual(f(1, b=None, c=2, d=3), ('1', None, dict(c=2, d=3)))
        self.assertEqual(f(1, b=4, c=2, d=3), ('1', '4', dict(c=2, d=3)))

    def test_default_none(self):
        @nutils.types.apply_annotations
        def f(a: str = None):
            return a
        self.assertEqual(f(), None)
        self.assertEqual(f(None), None)
        self.assertEqual(f(1), '1')


class nutils_hash(TestCase):

    class custom:
        @property
        def __nutils_hash__(self):
            return b'01234567890123456789'

        def f(self):
            pass

    def test_ellipsis(self):
        self.assertEqual(nutils.types.nutils_hash(...).hex(), '0c8bce06e451e4d5c49f60da0abf2ccbadf80600')

    def test_None(self):
        self.assertEqual(nutils.types.nutils_hash(None).hex(), 'bdfcbd663476b2db5b2b2e59a6d93882a908dc76')

    def test_bool(self):
        self.assertEqual(nutils.types.nutils_hash(False).hex(), '04a5e8f73dcea55dcd7482a476cf2e7b53d6dc50')
        self.assertEqual(nutils.types.nutils_hash(True).hex(), '3fe990437e1624c831729f2866979254437bb7e9')

    def test_int(self):
        self.assertEqual(nutils.types.nutils_hash(1).hex(), '00ec7dea895ebd921e56bbc554688d8b3a1e4dfc')
        self.assertEqual(nutils.types.nutils_hash(2).hex(), '8ae88fa39407cf75e46f9e0aba8c971de2256b14')

    def test_float(self):
        self.assertEqual(nutils.types.nutils_hash(1.).hex(), 'def4bae4f2a3e29f6ddac537d3fa7c72195e5d8b')
        self.assertEqual(nutils.types.nutils_hash(2.5).hex(), '5216c2bf3c16d8b8ff4d9b79f482e5cea0a4cb95')

    def test_complex(self):
        self.assertEqual(nutils.types.nutils_hash(1+0j).hex(), 'cf7a0d933b7bb8d3ca252683b137534a1ecae073')
        self.assertEqual(nutils.types.nutils_hash(2+1j).hex(), 'ee088890528f941a80aa842dad36591b05253e55')

    def test_inequality_numbers(self):
        self.assertNotEqual(nutils.types.nutils_hash(1).hex(), nutils.types.nutils_hash(1.).hex())
        self.assertNotEqual(nutils.types.nutils_hash(1).hex(), nutils.types.nutils_hash(1+0j).hex())
        self.assertNotEqual(nutils.types.nutils_hash(1).hex(), nutils.types.nutils_hash(True).hex())

    def test_str(self):
        self.assertEqual(nutils.types.nutils_hash('spam').hex(), '3ca1023ab75a68dc7b0f83b43ec624704a7aef61')
        self.assertEqual(nutils.types.nutils_hash('eggs').hex(), '124b0a7b3984e08125c380f7454896c1cad22e2c')

    def test_bytes(self):
        self.assertEqual(nutils.types.nutils_hash(b'spam').hex(), '5e717ec15aace7c25610c1dea340f2173f2df014')
        self.assertEqual(nutils.types.nutils_hash(b'eggs').hex(), '98f2061978497751cac94f982fd96d9b015b74c3')

    def test_tuple(self):
        self.assertEqual(nutils.types.nutils_hash(()).hex(), '15d44755bf0731b2a3e9a5c5c8e0807b61881a1f')
        self.assertEqual(nutils.types.nutils_hash((1,)).hex(), '328b16ebbc1815cf579ae038a35c4d68ebb022af')
        self.assertNotEqual(nutils.types.nutils_hash((1, 'spam')).hex(), nutils.types.nutils_hash(('spam', 1)).hex())

    def test_frozenset(self):
        self.assertEqual(nutils.types.nutils_hash(frozenset([1, 2])).hex(), '3862dc7e5321bc8a576c385ed2c12c71b96a375a')
        self.assertEqual(nutils.types.nutils_hash(frozenset(['spam', 'eggs'])).hex(), '2c75fd3db57f5e505e1425ae9ff6dcbbc77fd123')

    def test_ndarray(self):
        a = numpy.array([1, 2, 3])
        with self.assertRaises(TypeError):
            nutils.types.nutils_hash(a)
        a.flags.writeable = False
        self.assertEqual(nutils.types.nutils_hash(a).hex(),
                         '299c2c796b4a71b7a2b310ddb29bba0440d77e26' if numpy.int_ == numpy.int64
                         else '9fee185ee111495718c129b4d3a8ae79975f3459')

    @unittest.skipIf(sys.version_info < (3, 7), "not supported in this Python version")
    def test_dataclass(self):
        import dataclasses
        A = dataclasses.make_dataclass('A', [('n', int), ('f', float)])
        self.assertEqual(nutils.types.nutils_hash(A(n=1, f=2.5)).hex(), 'daf4235240e897beb9586db3c91663b24e229c52')

    def test_type_bool(self):
        self.assertEqual(nutils.types.nutils_hash(bool).hex(), 'feb912889d52d45fcd1e778c427b093a19a1ea78')

    def test_type_int(self):
        self.assertEqual(nutils.types.nutils_hash(int).hex(), 'aa8cb9975f7161b1f7ceb88b4b8585b49946b31e')

    def test_type_float(self):
        self.assertEqual(nutils.types.nutils_hash(float).hex(), '6d5079a53075f4b6f7710377838d8183730f1388')

    def test_type_complex(self):
        self.assertEqual(nutils.types.nutils_hash(complex).hex(), '6b00f6b9c6522742fd3f8054af6f10a24a671fff')

    def test_type_str(self):
        self.assertEqual(nutils.types.nutils_hash(str).hex(), '2349e11586163208d2581fe736630f4e4b680a7b')

    def test_type_bytes(self):
        self.assertEqual(nutils.types.nutils_hash(bytes).hex(), 'b0826ca666a48739e6f8b968d191adcefaa39670')

    def test_type_tuple(self):
        self.assertEqual(nutils.types.nutils_hash(tuple).hex(), '07cb4a24ca8ac53c820f20721432b4726e2ad1af')

    def test_type_frozenset(self):
        self.assertEqual(nutils.types.nutils_hash(frozenset).hex(), '48dc7cd0fbd54924498deb7c68dd363b4049f5e2')

    def test_type_bufferedreader(self):
        try:
            fid, path = tempfile.mkstemp()
            os.write(fid, b'test')
            os.close(fid)
            with open(path, 'rb') as f:
                f.seek(2)
                self.assertEqual(nutils.types.nutils_hash(f).hex(), '490e9467ce36ddf487999a7b43d554737385e42f')
                self.assertEqual(f.tell(), 2)
            with open(path, 'rb+') as f, self.assertRaises(TypeError):
                nutils.types.nutils_hash(f).hex()
        finally:
            os.unlink(path)

    def test_type_boundmethod(self):
        self.assertEqual(nutils.types.nutils_hash(self.custom().f).hex(), 'ebf7084bb2504922235ab035a9197b9cb4cf47af')

    def test_custom(self):
        self.assertEqual(nutils.types.nutils_hash(self.custom()).hex(), b'01234567890123456789'.hex())

    def test_unhashable(self):
        with self.assertRaises(TypeError):
            nutils.types.nutils_hash([])


class CacheMeta(TestCase):

    def test_property(self):

        for withslots in False, True:
            with self.subTest(withslots=withslots):

                class T(metaclass=nutils.types.CacheMeta):
                    if withslots:
                        __slots__ = ()
                    __cache__ = 'x',

                    @property
                    def x(self):
                        nonlocal ncalls
                        ncalls += 1
                        return 1

                ncalls = 0
                t = T()
                self.assertEqual(ncalls, 0)
                self.assertEqual(t.x, 1)
                self.assertEqual(ncalls, 1)
                self.assertEqual(t.x, 1)
                self.assertEqual(ncalls, 1)

    def test_set_property(self):

        class T(metaclass=nutils.types.CacheMeta):
            __cache__ = 'x',

            @property
            def x(self):
                return 1

        t = T()
        with self.assertRaises(AttributeError):
            t.x = 1

    def test_del_property(self):

        class T(metaclass=nutils.types.CacheMeta):
            __cache__ = 'x',

            @property
            def x(self):
                return 1

        t = T()
        with self.assertRaises(AttributeError):
            del t.x

    def test_method_without_args(self):

        for withslots in False, True:
            with self.subTest(withslots=withslots):

                class T(metaclass=nutils.types.CacheMeta):
                    if withslots:
                        __slots__ = ()
                    __cache__ = 'x',

                    def x(self):
                        nonlocal ncalls
                        ncalls += 1
                        return 1

                ncalls = 0
                t = T()
                self.assertEqual(ncalls, 0)
                self.assertEqual(t.x(), 1)
                self.assertEqual(ncalls, 1)
                self.assertEqual(t.x(), 1)
                self.assertEqual(ncalls, 1)

    def test_method_with_args(self):

        for withslots in False, True:
            with self.subTest(withslots=withslots):

                class T(metaclass=nutils.types.CacheMeta):
                    if withslots:
                        __slots__ = ()
                    __cache__ = 'x',

                    def x(self, a, b):
                        nonlocal ncalls
                        ncalls += 1
                        return a + b

                ncalls = 0
                t = T()
                self.assertEqual(ncalls, 0)
                self.assertEqual(t.x(1, 2), 3)
                self.assertEqual(ncalls, 1)
                self.assertEqual(t.x(a=1, b=2), 3)
                self.assertEqual(ncalls, 1)
                self.assertEqual(t.x(2, 2), 4)
                self.assertEqual(ncalls, 2)
                self.assertEqual(t.x(a=2, b=2), 4)
                self.assertEqual(ncalls, 2)
                self.assertEqual(t.x(1, 2), 3)
                self.assertEqual(ncalls, 3)

    def test_method_with_args_and_preprocessors(self):

        for withslots in False, True:
            with self.subTest(withslots=withslots):

                class T(metaclass=nutils.types.CacheMeta):
                    if withslots:
                        __slots__ = ()
                    __cache__ = 'x',

                    @nutils.types.apply_annotations
                    def x(self, a: int, b: int):
                        nonlocal ncalls
                        ncalls += 1
                        return a + b

                ncalls = 0
                t = T()
                self.assertEqual(ncalls, 0)
                self.assertEqual(t.x(1, 2), 3)
                self.assertEqual(ncalls, 1)
                self.assertEqual(t.x(a='1', b='2'), 3)
                self.assertEqual(ncalls, 1)
                self.assertEqual(t.x('2', '2'), 4)
                self.assertEqual(ncalls, 2)
                self.assertEqual(t.x(a=2, b=2), 4)
                self.assertEqual(ncalls, 2)
                self.assertEqual(t.x('1', 2), 3)
                self.assertEqual(ncalls, 3)

    def test_method_with_kwargs(self):

        for withslots in False, True:
            with self.subTest(withslots=withslots):

                class T(metaclass=nutils.types.CacheMeta):
                    if withslots:
                        __slots__ = ()
                    __cache__ = 'x',

                    def x(self, a, **kwargs):
                        nonlocal ncalls
                        ncalls += 1
                        return a + sum(kwargs.values())

                ncalls = 0
                t = T()
                self.assertEqual(ncalls, 0)
                self.assertEqual(t.x(1, b=2), 3)
                self.assertEqual(ncalls, 1)
                self.assertEqual(t.x(a=1, b=2), 3)
                self.assertEqual(ncalls, 1)
                self.assertEqual(t.x(1, b=2, c=3), 6)
                self.assertEqual(ncalls, 2)
                self.assertEqual(t.x(a=1, b=2, c=3), 6)
                self.assertEqual(ncalls, 2)

    def test_subclass_redefined_property(self):

        class T(metaclass=nutils.types.CacheMeta):
            __cache__ = 'x',

            @property
            def x(self):
                return 1

        class U(T):
            __cache__ = 'x',

            @property
            def x(self):
                return super().x + 1

            @property
            def y(self):
                return super().x

        u1 = U()
        self.assertEqual(u1.x, 2)
        self.assertEqual(u1.y, 1)

        u2 = U()
        self.assertEqual(u2.y, 1)
        self.assertEqual(u2.x, 2)

    def test_missing_attribute(self):

        with self.assertRaisesRegex(TypeError, 'Attribute listed in __cache__ is undefined: x'):
            class T(metaclass=nutils.types.CacheMeta):
                __cache__ = 'x',

    def test_invalid_attribute(self):

        with self.assertRaisesRegex(TypeError, "Don't know how to cache attribute x: None"):
            class T(metaclass=nutils.types.CacheMeta):
                __cache__ = 'x',
                x = None

    def test_name_mangling(self):

        for withslots in False, True:
            with self.subTest(withslots=withslots):

                class T(metaclass=nutils.types.CacheMeta):
                    if withslots:
                        __slots__ = ()
                    __cache__ = '__x',

                    @property
                    def __x(self):
                        nonlocal ncalls
                        ncalls += 1
                        return 1

                    @property
                    def y(self):
                        return self.__x

                ncalls = 0
                t = T()
                self.assertEqual(ncalls, 0)
                self.assertEqual(t.y, 1)
                self.assertEqual(ncalls, 1)
                self.assertEqual(t.y, 1)
                self.assertEqual(ncalls, 1)


class strictint(TestCase):

    def test_int(self):
        value = nutils.types.strictint(1)
        self.assertEqual(value, 1)
        self.assertEqual(type(value), int)

    def test_numpy_int(self):
        value = nutils.types.strictint(numpy.int64(1))
        self.assertEqual(value, 1)
        self.assertEqual(type(value), int)

    def test_float(self):
        with self.assertRaises(ValueError):
            nutils.types.strictint(1.)

    def test_numpy_float(self):
        with self.assertRaises(ValueError):
            nutils.types.strictint(numpy.float64(1.))

    def test_complex(self):
        with self.assertRaises(ValueError):
            nutils.types.strictint(1+0j)

    def test_str(self):
        with self.assertRaises(ValueError):
            nutils.types.strictint('1')


class strictfloat(TestCase):

    def test_int(self):
        value = nutils.types.strictfloat(1)
        self.assertEqual(value, 1.)
        self.assertEqual(type(value), float)

    def test_numpy_int(self):
        value = nutils.types.strictfloat(numpy.int64(1))
        self.assertEqual(value, 1.)
        self.assertEqual(type(value), float)

    def test_float(self):
        value = nutils.types.strictfloat(1.)
        self.assertEqual(value, 1.)
        self.assertEqual(type(value), float)

    def test_numpy_float(self):
        value = nutils.types.strictfloat(numpy.float64(1.))
        self.assertEqual(value, 1.)
        self.assertEqual(type(value), float)

    def test_complex(self):
        with self.assertRaises(ValueError):
            nutils.types.strictint(1+0j)

    def test_str(self):
        with self.assertRaises(ValueError):
            nutils.types.strictfloat('1.')


class strictstr(TestCase):

    def test_str(self):
        value = nutils.types.strictstr('spam')
        self.assertEqual(value, 'spam')
        self.assertEqual(type(value), str)

    def test_int(self):
        with self.assertRaises(ValueError):
            nutils.types.strictstr(1)


class strict(TestCase):

    def test_valid(self):
        self.assertEqual(nutils.types.strict[int](1), 1)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            nutils.types.strict[int]('1')

    def test_call(self):
        with self.assertRaises(TypeError):
            nutils.types.strict()


class tupletype(TestCase):

    def test_valid1(self):
        value = nutils.types.tuple[nutils.types.strictint]([])
        self.assertEqual(value, ())
        self.assertEqual(type(value), tuple)

    def test_valid2(self):
        value = nutils.types.tuple[nutils.types.strictint]([1, 2, 3])
        self.assertEqual(value, (1, 2, 3))
        self.assertEqual(type(value), tuple)

    def test_invalid(self):
        with self.assertRaises(ValueError):
            nutils.types.tuple[nutils.types.strictint]([1, 'spam', 'eggs'])

    def test_without_item_constructor(self):
        src = 1, 2, 3
        self.assertEqual(nutils.types.tuple(src), tuple(src))

    def test_name(self):
        self.assertEqual(nutils.types.tuple[nutils.types.strictint].__name__, 'tuple[nutils.types.strictint]')


class frozendict(TestCase):

    def test_constructor(self):
        src = {'spam': 1, 'eggs': 2.3}
        for name, value in [('mapping', src), ('mapping_view', src.items()), ('iterable', (item for item in src.items())), ('frozendict', nutils.types.frozendict(src))]:
            with self.subTest(name):
                frozen = nutils.types.frozendict(value)
                self.assertIsInstance(frozen, nutils.types.frozendict)
                self.assertEqual(dict(frozen), src)

    def test_constructor_invalid(self):
        with self.assertRaises(ValueError):
            nutils.types.frozendict(['spam', 'eggs', 1])

    def test_clsgetitem(self):
        T = nutils.types.frozendict[str, float]
        src = {1: 2, 'spam': '2.3'}
        for name, value in [('mapping', src), ('mapping_view', src.items()), ('iterable', (item for item in src.items()))]:
            with self.subTest(name):
                frozen = T(value)
                self.assertIsInstance(frozen, nutils.types.frozendict)
                self.assertEqual(dict(frozen), {'1': 2., 'spam': 2.3})

    def test_clsgetitem_invalid_types(self):
        with self.assertRaises(RuntimeError):
            nutils.types.frozendict[str, float, bool]

    def test_clsgetitem_invalid_value(self):
        T = nutils.types.frozendict[str, float]
        with self.assertRaises(ValueError):
            T(1)

    def test_setitem(self):
        frozen = nutils.types.frozendict({'spam': 1, 'eggs': 2.3})
        with self.assertRaises(TypeError):
            frozen['eggs'] = 3

    def test_delitem(self):
        frozen = nutils.types.frozendict({'spam': 1, 'eggs': 2.3})
        with self.assertRaises(TypeError):
            del frozen['eggs']

    def test_getitem_existing(self):
        frozen = nutils.types.frozendict({'spam': 1, 'eggs': 2.3})
        self.assertEqual(frozen['spam'], 1)

    def test_getitem_nonexisting(self):
        frozen = nutils.types.frozendict({'spam': 1, 'eggs': 2.3})
        with self.assertRaises(KeyError):
            frozen['foo']

    def test_contains(self):
        frozen = nutils.types.frozendict({'spam': 1, 'eggs': 2.3})
        self.assertIn('spam', frozen)
        self.assertNotIn('foo', frozen)

    def test_iter(self):
        src = {'spam': 1, 'eggs': 2.3}
        frozen = nutils.types.frozendict(src)
        self.assertEqual(frozenset(frozen), frozenset(src))

    def test_len(self):
        src = {'spam': 1, 'eggs': 2.3}
        frozen = nutils.types.frozendict(src)
        self.assertEqual(len(frozen), len(src))

    def test_hash(self):
        src = {'spam': 1, 'eggs': 2.3}
        self.assertEqual(hash(nutils.types.frozendict(src)), hash(nutils.types.frozendict(src)))

    def test_copy(self):
        src = {'spam': 1, 'eggs': 2.3}
        copy = nutils.types.frozendict(src).copy()
        self.assertIsInstance(copy, dict)
        self.assertEqual(copy, src)

    def test_pickle(self):
        src = {'spam': 1, 'eggs': 2.3}
        frozen = pickle.loads(pickle.dumps(nutils.types.frozendict(src)))
        self.assertIsInstance(frozen, nutils.types.frozendict)
        self.assertEqual(dict(frozen), src)

    def test_eq_same_id(self):
        src = {'spam': 1, 'eggs': 2.3}
        a = nutils.types.frozendict(src)
        self.assertEqual(a, a)

    def test_eq_other_id(self):
        src = {'spam': 1, 'eggs': 2.3}
        a = nutils.types.frozendict(src)
        b = nutils.types.frozendict(src)
        self.assertEqual(a, b)

    def test_eq_deduplicated(self):
        src = {'spam': 1, 'eggs': 2.3}
        a = nutils.types.frozendict(src)
        b = nutils.types.frozendict(src)
        a == b  # this replaces `a.__base` with `b.__base`
        self.assertEqual(a, b)

    def test_ineq_frozendict(self):
        src = {'spam': 1, 'eggs': 2.3}
        self.assertNotEqual(nutils.types.frozendict(src), nutils.types.frozendict({'spam': 1}))

    def test_ineq_dict(self):
        src = {'spam': 1, 'eggs': 2.3}
        self.assertNotEqual(nutils.types.frozendict(src), src)

    def test_nutils_hash(self):
        frozen = nutils.types.frozendict({'spam': 1, 'eggs': 2.3})
        self.assertEqual(nutils.types.nutils_hash(frozen).hex(), '8cf14f109e54707af9c2e66d7d3cdb755cce8243')


class frozenmultiset(TestCase):

    def test_constructor(self):
        src = 'spam', 'bacon', 'sausage', 'spam'
        for name, value in [('tuple', src), ('frozenmultiset', nutils.types.frozenmultiset(src))]:
            with self.subTest(name=name):
                frozen = nutils.types.frozenmultiset(value)
                for item in 'spam', 'bacon', 'sausage':
                    self.assertEqual({k: tuple(frozen).count(k) for k in set(src)}, {'spam': 2, 'bacon': 1, 'sausage': 1})

    def test_clsgetitem(self):
        src = False, 1, numpy.int64(2)
        frozen = nutils.types.frozenmultiset[nutils.types.strictint](src)
        self.assertEqual(set(frozen), {0, 1, 2})

    def test_preserve_order(self):
        for src in [('spam', 'bacon', 'sausage', 'spam'), ('spam', 'egg', 'spam', 'spam', 'bacon', 'spam')]:
            with self.subTest(src=src):
                self.assertEqual(tuple(nutils.types.frozenmultiset(src)), src)

    def test_and(self):
        for l, r, lar in [[['spam', 'eggs'], ['spam', 'spam', 'eggs'], ['spam', 'eggs']],
                          [['spam'], ['eggs'], []],
                          [['spam', 'spam']]*3]:
            with self.subTest(l=l, r=r, lar=lar):
                self.assertEqual(nutils.types.frozenmultiset(l) & nutils.types.frozenmultiset(r), nutils.types.frozenmultiset(lar))
            with self.subTest(l=r, r=l, lar=lar):
                self.assertEqual(nutils.types.frozenmultiset(r) & nutils.types.frozenmultiset(l), nutils.types.frozenmultiset(lar))

    def test_sub(self):
        for l, r, lmr, rml in [[['spam', 'eggs'], ['spam', 'spam', 'eggs'], [], ['spam']],
                               [['spam'], ['eggs'], ['spam'], ['eggs']],
                               [['spam'], ['spam'], [], []]]:
            with self.subTest(l=l, r=r, lmr=lmr):
                self.assertEqual(nutils.types.frozenmultiset(l)-nutils.types.frozenmultiset(r), nutils.types.frozenmultiset(lmr))
            with self.subTest(l=r, r=l, lmr=rml):
                self.assertEqual(nutils.types.frozenmultiset(r)-nutils.types.frozenmultiset(l), nutils.types.frozenmultiset(rml))

    def test_pickle(self):
        src = 'spam', 'bacon', 'sausage', 'spam'
        frozen = pickle.loads(pickle.dumps(nutils.types.frozenmultiset(src)))
        self.assertIsInstance(frozen, nutils.types.frozenmultiset)
        self.assertEqual(frozen, nutils.types.frozenmultiset(src))

    def test_hash(self):
        src = 'spam', 'bacon', 'sausage', 'spam'
        ref = nutils.types.frozenmultiset(src)
        for perm in itertools.permutations(src):
            with self.subTest(perm=perm):
                self.assertEqual(hash(nutils.types.frozenmultiset(src)), hash(ref))

    def test_nutils_hash(self):
        for perm in itertools.permutations(('spam', 'bacon', 'sausage', 'spam')):
            with self.subTest(perm=perm):
                frozen = nutils.types.frozenmultiset(perm)
                self.assertEqual(nutils.types.nutils_hash(frozen).hex(), 'f3fd9c6d4741af2e67973457ee6308deddcb714c')

    def test_eq(self):
        src = 'spam', 'bacon', 'sausage', 'spam'
        ref = nutils.types.frozenmultiset(src)
        for perm in itertools.permutations(src):
            with self.subTest(perm=perm):
                self.assertEqual(nutils.types.frozenmultiset(src), ref)

    def test_contains(self):
        src = 'spam', 'bacon', 'sausage', 'spam'
        frozen = nutils.types.frozenmultiset(src)
        for item in 'spam', 'bacon', 'eggs':
            with self.subTest(item=item):
                if item in src:
                    self.assertIn(item, frozen)
                else:
                    self.assertNotIn(item, frozen)

    def test_len(self):
        src = 'spam', 'bacon', 'sausage', 'spam'
        frozen = nutils.types.frozenmultiset(src)
        self.assertEqual(len(frozen), len(src))

    def test_nonzero(self):
        self.assertTrue(nutils.types.frozenmultiset(['spam', 'eggs']))
        self.assertFalse(nutils.types.frozenmultiset([]))

    def test_add(self):
        l = nutils.types.frozenmultiset(['spam', 'bacon'])
        r = nutils.types.frozenmultiset(['sausage', 'spam'])
        lpr = nutils.types.frozenmultiset(['spam', 'bacon', 'sausage', 'spam'])
        self.assertEqual(l+r, lpr)

    def test_isdisjoint(self):
        for l, r, disjoint in [[['spam', 'eggs'], ['spam', 'spam', 'eggs'], False],
                               [['spam'], ['eggs'], True],
                               [['spam'], ['spam'], False]]:
            with self.subTest(l=l, r=r, disjoint=disjoint):
                self.assertEqual(nutils.types.frozenmultiset(l).isdisjoint(nutils.types.frozenmultiset(r)), disjoint)


class frozenarray(TestCase):

    def test_generic(self):
        a = 1
        f = nutils.types.frozenarray(a)
        self.assertIsInstance(f, numpy.generic)
        self.assertFalse(f.flags.writeable)
        self.assertEqual(f.dtype, int)

    def test_generic_passthrough(self):
        a = numpy.int_(1)
        f = nutils.types.frozenarray(a)
        self.assertIs(f, a)

    def test_array(self):
        a = 1, 2, 3
        f = nutils.types.frozenarray(a)
        self.assertIsInstance(f, numpy.ndarray)
        self.assertFalse(f.flags.writeable)
        self.assertEqual(f.dtype, int)

    def test_cast(self):
        a = numpy.array([1, 2, 3])
        a.flags.writeable = False
        f = nutils.types.frozenarray(a, dtype=float)
        self.assertIsInstance(f, numpy.ndarray)
        self.assertFalse(f.flags.writeable)
        self.assertEqual(f.dtype, float)

    def test_passthrough(self):
        a = numpy.array([1, 2, 3])
        a.flags.writeable = False
        b = a[1:][:-1]  # multiple bases
        f = nutils.types.frozenarray(b)
        self.assertIs(f, b)

    def test_copy(self):
        a = numpy.array([1, 2, 3])
        b = a[1:]
        b.flags.writeable = False
        f = nutils.types.frozenarray(b)
        self.assertIsNot(f, b)

    def test_nocopy(self):
        a = numpy.array([1, 2, 3])
        b = a[1:]
        f = nutils.types.frozenarray(b, copy=False)
        self.assertIs(f, b)
        self.assertFalse(b.flags.writeable)
        self.assertFalse(a.flags.writeable)


class T_Immutable(nutils.types.Immutable):
    def __init__(self, x, y, *, z):
        pass


class T_Singleton(nutils.types.Singleton):
    def __init__(self, x, y, *, z):
        pass


@parametrize
class ImmutableFamily(TestCase):

    def test_pickle(self):
        T = {nutils.types.Immutable: T_Immutable, nutils.types.Singleton: T_Singleton}[self.cls]
        a = T(1, 2, z=3)
        b = pickle.loads(pickle.dumps(a))
        self.assertEqual(a, b)

    def test_eq(self):
        class T(self.cls):
            def __init__(self, x, y):
                pass

        class U(self.cls):
            def __init__(self, x, y):
                pass

        self.assertEqual(T(1, 2), T(1, 2))
        self.assertNotEqual(T(1, 2), T(2, 1))
        self.assertNotEqual(T(1, 2), U(1, 2))

    def test_canonical_args(self):
        class T(self.cls):
            def __init__(self, x, y, z=3):
                pass

        self.assertEqual(T(x=1, y=2), T(1, 2, 3))

    def test_keyword_args(self):
        class T(self.cls):
            def __init__(self, x, y, **kwargs):
                pass

        a = T(x=1, y=2, z=3)
        b = T(1, 2, z=3)
        self.assertEqual(a, b)

    def test_preprocessors(self):
        class T(self.cls):
            @nutils.types.apply_annotations
            def __init__(self, x: int):
                pass

        self.assertEqual(T(1), T('1'))
        self.assertEqual(T(1), T(x='1'))

    def test_nutils_hash(self):
        class T(self.cls):
            def __init__(self, x, y):
                pass

        class T1(self.cls, version=1):
            def __init__(self, x, y):
                pass

        class U(self.cls):
            def __init__(self, x, y):
                pass

        self.assertEqual(nutils.types.nutils_hash(T(1, 2)).hex(), nutils.types.nutils_hash(T(1, 2)).hex())
        self.assertNotEqual(nutils.types.nutils_hash(T(1, 2)).hex(), nutils.types.nutils_hash(T(2, 1)).hex())
        self.assertNotEqual(nutils.types.nutils_hash(T(1, 2)).hex(), nutils.types.nutils_hash(U(1, 2)).hex())
        # Since the hash does not include base classes, the hashes of Immutable and Singleton are the same.
        self.assertEqual(nutils.types.nutils_hash(T(1, 2)).hex(), '2f7fb825b73398a20ef5f95649429c75d7a9d615')
        self.assertEqual(nutils.types.nutils_hash(T1(1, 2)).hex(), 'b907c718a9a7e8c28300e028cfbb578a608f7620')

    @parametrize.enable_if(lambda cls: cls is nutils.types.Singleton)
    def test_deduplication(self):
        class T(self.cls):
            def __init__(self, x, y):
                pass

        class U(self.cls):
            def __init__(self, x, y):
                pass

        a = T(1, 2)
        b = T(1, 2)
        c = T(2, 1)
        d = U(1, 2)
        self.assertIs(a, b)
        self.assertEqual(a, b)
        self.assertIsNot(a, c)
        self.assertNotEqual(a, c)
        self.assertIsNot(a, d)
        self.assertNotEqual(a, d)


ImmutableFamily(cls=nutils.types.Immutable)
ImmutableFamily(cls=nutils.types.Singleton)


class arraydata(TestCase):

    def _check(self, array, dtype):
        arraydata = nutils.types.arraydata(array)
        self.assertEqual(arraydata.shape, array.shape)
        self.assertEqual(arraydata.ndim, array.ndim)
        self.assertEqual(arraydata.dtype, dtype)
        self.assertAllEqual(numpy.asarray(arraydata), array)

    def test_bool(self):
        self._check(numpy.array([True, False, True]), bool)

    def test_int(self):
        for d in 'int32', 'int64', 'uint32':
            with self.subTest(d):
                self._check(numpy.array([[1, 2, 3], [4, 5, 6]], dtype=d), int)

    def test_float(self):
        for d in 'float32', 'float64':
            with self.subTest(d):
                self._check(numpy.array([[.1, .2, .3], [.4, .5, .6]], dtype=d), float)

    def test_complex(self):
        self._check(numpy.array([1+2j, 3+4j]), complex)

    def test_rewrap(self):
        w = nutils.types.arraydata(numpy.array([1, 2, 3]))
        self.assertIs(w, nutils.types.arraydata(w))

    def test_pickle(self):
        import pickle
        orig = nutils.types.arraydata([1, 2, 3])
        s = pickle.dumps(orig)
        unpickled = pickle.loads(s)
        self.assertEqual(orig, unpickled)
        self.assertAllEqual(numpy.asarray(unpickled), [1, 2, 3])

    def test_hash(self):
        a = nutils.types.arraydata(numpy.array([1, 2, 3], dtype=numpy.int32))
        b = nutils.types.arraydata(numpy.array([1, 2, 3], dtype=numpy.int64))
        c = nutils.types.arraydata(numpy.array([[1, 2, 3]], dtype=numpy.int64))
        self.assertEqual(hash(a), hash(b))
        self.assertEqual(a, b)
        self.assertNotEqual(hash(a), hash(c))  # shapes differ
        self.assertNotEqual(a, c)


class lru_cache(TestCase):

    def setUp(self):
        super().setUp()
        self.func.cache.clear()

    class obj(nutils.types.Immutable):
        'weak referencable object'

    @nutils.types.lru_cache
    def func(self, *args):
        self.called = True
        return self.obj()

    @contextlib.contextmanager
    def assertCached(self, *args):
        self.called = False
        yield
        self.assertFalse(self.called)

    @contextlib.contextmanager
    def assertNotCached(self, *args):
        self.called = False
        yield
        self.assertTrue(self.called)

    def test_array_identification(self):
        a = numpy.array([1, 2, 3, 4])
        a.flags.writeable = False
        with self.assertNotCached():
            self.func(a[1:][:-1])
        with self.assertCached():
            self.func(a[:-1][1:])

    def test_destruction_arrays(self):
        a = numpy.array([1, 2, 3, 4])
        a.flags.writeable = False
        b = numpy.array([5, 6, 7, 8])
        b.flags.writeable = False
        with self.assertNotCached():
            ret_ = weakref.ref(self.func(a, b))
        with self.assertCached():
            self.assertIs(ret_(), self.func(a, b))
        del a
        self.assertIs(ret_(), None)

    def test_destruction_array_obj(self):
        a = numpy.array([1, 2, 3, 4])
        a.flags.writeable = False
        b = self.obj()
        b_ = weakref.ref(b)
        with self.assertNotCached():
            ret_ = weakref.ref(self.func(a, b))
        del b
        self.assertIsNot(b_(), None)
        self.assertIsNot(ret_(), None)
        del a
        self.assertIs(b_(), None)
        self.assertIs(ret_(), None)

    def test_mutable(self):
        a = numpy.array([1, 2, 3, 4])
        with self.assertNotCached():
            self.func(a)
        with self.assertNotCached():
            self.func(a)


class hashable_function(TestCase):

    def test_hash(self):
        def func(): pass
        self.assertEqual(nutils.types.nutils_hash(nutils.types.hashable_function('a')(func)).hex(), 'b4e9593d1bbb26059a5c6665b4a3bc15cf7a0d91')
        self.assertEqual(nutils.types.nutils_hash(nutils.types.hashable_function('b')(func)).hex(), '4b0f56560e408925fc65fabc2ba220ed7d62e10d')

    def test_equality(self):

        @nutils.types.hashable_function('a')
        def f(): pass

        @nutils.types.hashable_function('a')
        def g(): pass

        @nutils.types.hashable_function('b')
        def h(): pass

        self.assertEqual(f, g)
        self.assertEqual(hash(f), hash(g))
        self.assertNotEqual(f, h)

    def test_function(self):

        @nutils.types.hashable_function('f')
        def f(arg):
            return arg

        self.assertEqual(f(1), 1)

    def test_method(self):

        class Test:

            @nutils.types.hashable_function('f')
            def f(arg):
                return arg

        self.assertEqual(Test.f(1), 1)
        self.assertEqual(Test().f(1), 1)

# vim:sw=2:sts=2:et
