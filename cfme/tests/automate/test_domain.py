# -*- coding: utf-8 -*-
import fauxfactory
import pytest

from cfme.automate.explorer.domain import DomainCollection

from utils import error
from utils.appliance.implementations.ui import navigate_to
from utils.update import update


@pytest.mark.tier(1)
@pytest.mark.parametrize('enabled', [True, False], ids=['enabled', 'disabled'])
def test_domain_crud(request, enabled):
    domains = DomainCollection()
    domain = domains.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha(),
        enabled=enabled)
    request.addfinalizer(domain.delete_if_exists)
    assert domain.exists
    view = navigate_to(domain, 'Details')
    if enabled:
        assert 'Disabled' not in view.title.text
    else:
        assert 'Disabled' in view.title.text
    updated_description = "editdescription{}".format(fauxfactory.gen_alpha())
    with update(domain):
        domain.description = updated_description
    view = navigate_to(domain, 'Edit')
    assert view.description.value == updated_description
    assert domain.exists
    domain.delete(cancel=True)
    assert domain.exists
    domain.delete()
    assert not domain.exists


@pytest.mark.tier(1)
def test_domain_delete_from_table(request):
    domains = DomainCollection()
    generated = []
    for _ in range(3):
        domain = domains.create(
            name=fauxfactory.gen_alpha(),
            description=fauxfactory.gen_alpha(),
            enabled=True)
        request.addfinalizer(domain.delete_if_exists)
        generated.append(domain)

    domains.delete(*generated)
    for domain in generated:
        assert not domain.exists


@pytest.mark.tier(2)
def test_duplicate_domain_disallowed(request):
    domains = DomainCollection()
    domain = domains.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha(),
        enabled=True)
    request.addfinalizer(domain.delete_if_exists)
    with error.expected("Name has already been taken"):
        domains.create(
            name=domain.name,
            description=domain.description,
            enabled=domain.enabled)


@pytest.mark.tier(2)
def test_cannot_delete_builtin():
    domains = DomainCollection()
    manageiq_domain = domains.instantiate(name='ManageIQ')
    details_view = navigate_to(manageiq_domain, 'Details')
    if domains.appliance.version < '5.7':
        assert details_view.configuration.is_displayed
        assert 'Remove this Domain' not in details_view.configuration.items
    else:
        assert not details_view.configuration.is_displayed


@pytest.mark.tier(2)
def test_cannot_edit_builtin():
    domains = DomainCollection()
    manageiq_domain = domains.instantiate(name='ManageIQ')
    details_view = navigate_to(manageiq_domain, 'Details')
    if domains.appliance.version < '5.7':
        assert details_view.configuration.is_displayed
        assert not details_view.configuration.item_enabled('Edit this Domain')
    else:
        assert not details_view.configuration.is_displayed


@pytest.mark.tier(2)
def test_domain_name_wrong():
    domains = DomainCollection()
    with error.expected('Name may contain only'):
        domains.create(name='with space')


@pytest.mark.tier(2)
def test_domain_lock_unlock(request):
    domains = DomainCollection()
    domain = domains.create(
        name=fauxfactory.gen_alpha(),
        description=fauxfactory.gen_alpha(),
        enabled=True)
    request.addfinalizer(domain.delete)
    ns1 = domain.namespaces.create(name='ns1')
    ns2 = ns1.namespaces.create(name='ns2')
    cls = ns2.classes.create(name='class1')
    cls.schema.add_field(name='myfield', type='Relationship')
    inst = cls.instances.create(name='inst')
    meth = cls.methods.create(name='meth', script='$evm')
    # Lock the domain
    domain.lock()
    # Check that nothing is editable
    # namespaces
    details = navigate_to(ns1, 'Details')
    assert not details.configuration.is_displayed
    details = navigate_to(ns2, 'Details')
    assert not details.configuration.is_displayed
    # class
    details = navigate_to(cls, 'Details')
    assert details.configuration.items == ['Copy selected Instances']
    assert not details.configuration.item_enabled('Copy selected Instances')
    details.schema.select()
    assert not details.configuration.is_displayed
    # instance
    details = navigate_to(inst, 'Details')
    assert details.configuration.items == ['Copy this Instance']
    # method
    details = navigate_to(meth, 'Details')
    assert details.configuration.items == ['Copy this Method']
    # Unlock it
    domain.unlock()
    # Check that it is editable
    with update(ns1):
        ns1.name = 'UpdatedNs1'
    assert ns1.exists
    with update(ns2):
        ns2.name = 'UpdatedNs2'
    assert ns2.exists
    with update(cls):
        cls.name = 'UpdatedClass'
    assert cls.exists
    cls.schema.add_field(name='myfield2', type='Relationship')
    with update(inst):
        inst.name = 'UpdatedInstance'
    assert inst.exists
    with update(meth):
        meth.name = 'UpdatedMethod'
    assert meth.exists
