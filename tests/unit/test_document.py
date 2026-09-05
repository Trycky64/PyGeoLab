"""Exercise document identity, atomic changes, recalculation, and invalid constructions."""

from collections.abc import MutableMapping
from dataclasses import replace
from typing import cast
from uuid import uuid4

import pytest

from pygeolab.geometry.primitives import Point2D, Segment2D
from pygeolab.model.document import Document
from pygeolab.model.objects import GeoObject


def _point(name: str, x: float = 0, y: float = 0) -> GeoObject:
    """Create a free point using the persistent object representation."""
    return GeoObject(kind="point", name=name, params={"x": x, "y": y})


def _assert_point(value: GeoObject, x: float, y: float) -> None:
    """Check the validity and approximate coordinates of a computed point."""
    assert value.valid
    assert value.error_state is None
    assert isinstance(value.geometry, Point2D)
    assert (value.geometry.x, value.geometry.y) == pytest.approx((x, y))


def _construction() -> tuple[Document, GeoObject, GeoObject, GeoObject, GeoObject, GeoObject]:
    """Build a dependency chain and an independent point for document scenarios."""
    document = Document(name="Construction")
    first = document.add(_point("A", 0, 0))
    second = document.add(_point("B", 4, 2))
    midpoint = document.add(
        GeoObject(kind="midpoint", name="M", dependencies=(first.id, second.id))
    )
    segment = document.add(
        GeoObject(kind="segment", name="s", dependencies=(midpoint.id, second.id))
    )
    independent = document.add(_point("C", 9, 7))
    return document, first, second, midpoint, segment, independent


def test_add_computes_geometry_and_preserves_stable_identity() -> None:
    """Registration computes the object while retaining its UUID and visible name."""
    document = Document(name="Triangle")
    original = _point("A", 1.5, -2)
    initial_revision = document.revision

    registered = document.add(original)

    assert document.name == "Triangle"
    assert registered.id == original.id
    assert registered.name == "A"
    assert document.get(original.id) is registered
    assert document.objects[original.id] is registered
    assert document.revision > initial_revision
    _assert_point(registered, 1.5, -2)


def test_registry_cannot_be_modified_outside_document_operations() -> None:
    """External registry writes cannot bypass document validation or notification."""
    document = Document(name="Registry")
    point = document.add(_point("A"))
    registry = cast(MutableMapping[str, GeoObject], document.objects)

    with pytest.raises(TypeError):
        registry[point.id] = _point("Replacement")
    with pytest.raises(TypeError):
        del registry[point.id]

    assert document.get(point.id) is point


def test_rename_preserves_uuid_and_all_dependencies() -> None:
    """Names are editable display labels and never serve as dependency identities."""
    document, first, second, midpoint, segment, _ = _construction()

    renamed = document.update(first.id, name="Origin")

    assert renamed.id == first.id
    assert renamed.name == "Origin"
    assert document.get(midpoint.id).dependencies == (first.id, second.id)
    assert document.get(segment.id).dependencies == (midpoint.id, second.id)
    _assert_point(document.get(midpoint.id), 2, 1)


@pytest.mark.parametrize("duplicate", ["id", "name"])
def test_duplicate_identity_or_name_is_rejected_atomically(duplicate: str) -> None:
    """A failed addition leaves the existing registry and document revision intact."""
    document = Document(name="Uniqueness")
    existing = document.add(_point("A"))
    candidate = _point("B", 3, 4)
    candidate = replace(candidate, **{duplicate: getattr(existing, duplicate)})
    revision = document.revision

    with pytest.raises(ValueError):
        document.add(candidate)

    assert tuple(document.objects) == (existing.id,)
    assert document.get(existing.id) is existing
    assert document.revision == revision


@pytest.mark.parametrize("name", ["", "   ", "\t\n"])
def test_empty_display_names_cannot_enter_the_registry(name: str) -> None:
    """Every document object must have a nonempty user-facing name."""
    document = Document(name="Names")

    with pytest.raises(ValueError):
        document.add(_point(name))

    assert not document.objects


def test_update_cannot_change_an_objects_uuid() -> None:
    """Replacing an identity would break dependent objects and must be refused."""
    document, first, _, midpoint, _, _ = _construction()
    revision = document.revision

    with pytest.raises(ValueError):
        document.update(first.id, id=str(uuid4()))

    assert document.get(first.id).id == first.id
    assert document.get(midpoint.id).dependencies[0] == first.id
    assert document.revision == revision


def test_conflicting_rename_rolls_back_without_replacing_existing_objects() -> None:
    """A failed rename leaves both labels, identities, and computed state untouched."""
    document, first, second, _, _, _ = _construction()
    before = dict(document.objects)
    revision = document.revision

    with pytest.raises(ValueError):
        document.update(first.id, name=second.name)

    assert document.revision == revision
    assert set(document.objects) == set(before)
    assert all(document.get(identifier) is value for identifier, value in before.items())


def test_moving_a_point_recomputes_only_its_descendants_in_dependency_order() -> None:
    """A parent move updates the whole affected chain while preserving independent values."""
    document, first, second, midpoint, segment, independent = _construction()
    untouched_second = document.get(second.id)
    untouched_independent = document.get(independent.id)

    moved = document.move_point(first.id, Point2D(2, 4))

    _assert_point(moved, 2, 4)
    _assert_point(document.get(midpoint.id), 3, 3)
    geometry = document.get(segment.id).geometry
    assert isinstance(geometry, Segment2D)
    assert (geometry.start.x, geometry.start.y) == pytest.approx((3, 3))
    assert (geometry.end.x, geometry.end.y) == pytest.approx((4, 2))
    order = document.last_recomputed
    assert set(order) == {first.id, midpoint.id, segment.id}
    assert order.index(first.id) < order.index(midpoint.id) < order.index(segment.id)
    assert document.get(second.id) is untouched_second
    assert document.get(independent.id) is untouched_independent


def test_missing_dependency_update_is_atomic() -> None:
    """A dangling reference cannot partially replace an object or recalculate descendants."""
    document, first, _, midpoint, _, _ = _construction()
    before = dict(document.objects)
    revision = document.revision

    with pytest.raises(ValueError):
        document.update(midpoint.id, dependencies=(first.id, str(uuid4())))

    assert document.revision == revision
    assert set(document.objects) == set(before)
    assert all(document.get(identifier) is value for identifier, value in before.items())


def test_cycle_update_is_atomic() -> None:
    """An edge back to a descendant is rejected before the document changes."""
    document, first, second, midpoint, _, _ = _construction()
    before = dict(document.objects)
    revision = document.revision

    with pytest.raises(ValueError):
        document.update(first.id, kind="midpoint", dependencies=(midpoint.id, second.id), params={})

    assert document.revision == revision
    assert all(document.get(identifier) is value for identifier, value in before.items())


def test_remove_cascades_and_restore_accepts_children_before_parents() -> None:
    """Deleted dependent objects can be restored as a complete unordered batch."""
    document, first, second, midpoint, segment, independent = _construction()

    removed = document.remove(first.id)

    assert {value.id for value in removed} == {first.id, midpoint.id, segment.id}
    assert set(document.objects) == {second.id, independent.id}
    removed_by_id = {value.id: value for value in removed}
    document.restore(
        [removed_by_id[segment.id], removed_by_id[midpoint.id], removed_by_id[first.id]]
    )

    assert set(document.objects) == {first.id, second.id, midpoint.id, segment.id, independent.id}
    _assert_point(document.get(midpoint.id), 2, 1)
    assert document.get(segment.id).valid
    assert document.get(segment.id).dependencies == (midpoint.id, second.id)


def test_restore_validates_the_whole_batch_before_registration() -> None:
    """An invalid batch cannot leave earlier valid objects registered behind it."""
    document = Document(name="Restore")
    existing = document.add(_point("A"))
    valid = _point("B", 4, 2)
    invalid = GeoObject(kind="segment", name="s", dependencies=(valid.id, str(uuid4())))
    revision = document.revision

    with pytest.raises(ValueError):
        document.restore([valid, invalid])

    assert tuple(document.objects) == (existing.id,)
    assert document.get(existing.id) is existing
    assert document.revision == revision


def test_restore_rejects_a_cycle_inside_an_unordered_batch() -> None:
    """Mutually dependent new values cannot be accepted by batch restoration."""
    document = Document(name="Cycle")
    anchor = document.add(_point("A"))
    first_id, second_id = str(uuid4()), str(uuid4())
    first = GeoObject(id=first_id, kind="midpoint", name="M", dependencies=(second_id, anchor.id))
    second = GeoObject(id=second_id, kind="midpoint", name="N", dependencies=(first_id, anchor.id))
    revision = document.revision

    with pytest.raises(ValueError):
        document.restore([second, first])

    assert tuple(document.objects) == (anchor.id,)
    assert document.revision == revision


def test_impossible_construction_and_descendants_recover_after_parent_move() -> None:
    """Invalid geometry stays registered and becomes valid again when inputs permit it."""
    document = Document(name="Recovery")
    first = document.add(_point("A", 0, 0))
    second = document.add(_point("B", 0, 0))
    third = document.add(_point("C", 1, -1))
    fourth = document.add(_point("D", 1, 1))
    line = document.add(GeoObject(kind="line", name="d", dependencies=(first.id, second.id)))
    other_line = document.add(GeoObject(kind="line", name="e", dependencies=(third.id, fourth.id)))
    crossing = document.add(
        GeoObject(kind="intersection", name="P", dependencies=(line.id, other_line.id))
    )
    midpoint = document.add(
        GeoObject(kind="midpoint", name="M", dependencies=(first.id, crossing.id))
    )

    for identifier in (line.id, crossing.id, midpoint.id):
        value = document.get(identifier)
        assert not value.valid
        assert value.geometry is None
        assert isinstance(value.error_state, str)
        assert value.error_state.strip()

    document.move_point(second.id, Point2D(2, 0))

    assert document.get(line.id).valid
    _assert_point(document.get(crossing.id), 1, 0)
    _assert_point(document.get(midpoint.id), 0.5, 0)


def test_locked_free_points_cannot_be_moved() -> None:
    """Document movement enforces the object's lock before changing its state."""
    document = Document(name="Locks")
    point = document.add(replace(_point("A", 1, 2), locked=True))
    revision = document.revision

    with pytest.raises(ValueError):
        document.move_point(point.id, Point2D(5, 6))

    _assert_point(document.get(point.id), 1, 2)
    assert document.revision == revision


def test_overflowing_distance_is_preserved_as_an_invalid_object() -> None:
    """A nonfinite distance remains recoverable document state instead of crashing."""
    document = Document(name="Overflow")
    first = document.add(_point("A", -1e308, 0))
    second = document.add(_point("B", 1e308, 0))

    distance = document.add(
        GeoObject(kind="distance", name="length", dependencies=(first.id, second.id))
    )

    assert document.get(distance.id) is distance
    assert not distance.valid
    assert distance.geometry is None
    assert isinstance(distance.error_state, str)
    assert distance.error_state.strip()


def test_calculated_points_cannot_be_moved_as_free_points() -> None:
    """A derived point's position stays controlled by its dependencies."""
    document, _, _, midpoint, _, _ = _construction()
    revision = document.revision

    with pytest.raises(ValueError):
        document.move_point(midpoint.id, Point2D(5, 6))

    _assert_point(document.get(midpoint.id), 2, 1)
    assert document.revision == revision


def test_observers_see_complete_changes_and_can_unsubscribe() -> None:
    """Notifications run once per document action after all dependent geometry is current."""
    document, first, _, midpoint, _, _ = _construction()
    notifications: list[tuple[float, float]] = []

    def on_change() -> None:
        """Capture the derived position visible to a subscribed UI observer."""
        geometry = document.get(midpoint.id).geometry
        assert isinstance(geometry, Point2D)
        notifications.append((geometry.x, geometry.y))

    unsubscribe = document.subscribe(on_change)
    document.move_point(first.id, Point2D(2, 4))

    assert len(notifications) == 1
    assert notifications[0] == pytest.approx((3, 3))

    with pytest.raises(ValueError):
        document.update(first.id, name="B")
    assert len(notifications) == 1

    unsubscribe()
    document.move_point(first.id, Point2D(4, 6))
    assert len(notifications) == 1


def test_unique_names_are_available_without_mutating_document() -> None:
    """Automatic labels avoid existing names while leaving registration to the caller."""
    document = Document(name="Automatic names")
    document.add(_point("A"))
    document.add(_point("A1"))
    revision = document.revision

    available = document.unique_name("A")

    assert available.startswith("A")
    assert available not in {value.name for value in document.objects.values()}
    assert document.revision == revision
    document.add(_point(available))
    assert document.unique_name("A") != available
