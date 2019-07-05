/***************************************************************************
 *                                                                         *
 * Copyright (C) 2007-2015 by frePPLe bvba                                 *
 *                                                                         *
 * This library is free software; you can redistribute it and/or modify it *
 * under the terms of the GNU Affero General Public License as published   *
 * by the Free Software Foundation; either version 3 of the License, or    *
 * (at your option) any later version.                                     *
 *                                                                         *
 * This library is distributed in the hope that it will be useful,         *
 * but WITHOUT ANY WARRANTY; without even the implied warranty of          *
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the            *
 * GNU Affero General Public License for more details.                     *
 *                                                                         *
 * You should have received a copy of the GNU Affero General Public        *
 * License along with this program.                                        *
 * If not, see <http://www.gnu.org/licenses/>.                             *
 *                                                                         *
 ***************************************************************************/

#define FREPPLE_CORE
#include "frepple/model.h"

namespace frepple
{

template<class Resource> Tree utils::HasName<Resource>::st;
const MetaCategory* Resource::metadata;
const MetaClass* ResourceDefault::metadata;
const MetaClass* ResourceInfinite::metadata;
const MetaClass* ResourceBuckets::metadata;

Duration Resource::defaultMaxEarly(100*86400L);


int Resource::initialize()
{
  // Initialize the metadata
  metadata = MetaCategory::registerCategory<Resource>("resource", "resources", reader, finder);
  registerFields<Resource>(const_cast<MetaCategory*>(metadata));

  // Initialize the Python class
  PythonType& x = FreppleCategory<Resource>::getPythonType();
  x.addMethod(
    "plan", Resource::plan, METH_VARARGS,
    "Return an iterator with tuples representing the resource plan in each time bucket"
    );
  x.addMethod(
    "inspect", inspectPython, METH_VARARGS,
    "debugging function to print the resource profile"
    );
  return FreppleCategory<Resource>::initialize();
}


int ResourceDefault::initialize()
{
  // Initialize the metadata
  ResourceDefault::metadata = MetaClass::registerClass<ResourceDefault>(
    "resource", "resource_default",
    Object::create<ResourceDefault>,
    true
    );

  // Initialize the Python class
  return FreppleClass<ResourceDefault,Resource>::initialize();
}


int ResourceInfinite::initialize()
{
  // Initialize the metadata
  ResourceInfinite::metadata = MetaClass::registerClass<ResourceInfinite>(
    "resource", "resource_infinite",
    Object::create<ResourceInfinite>
    );

  // Initialize the Python class
  return FreppleClass<ResourceInfinite,Resource>::initialize();
}


int ResourceBuckets::initialize()
{
  // Initialize the metadata
  ResourceBuckets::metadata = MetaClass::registerClass<ResourceBuckets>(
    "resource",
    "resource_buckets",
    Object::create<ResourceBuckets>);
  registerFields<ResourceBuckets>(const_cast<MetaClass*>(metadata));

  // Initialize the Python class
  FreppleClass<ResourceBuckets, Resource>::getPythonType().addMethod(
    "computeAvailability", ResourceBuckets::computeBucketAvailability, METH_VARARGS,
    "Convert the maximum and availability calendar into quantities available per capacity bucket"
    );
  return FreppleClass<ResourceBuckets, Resource>::initialize();
}


void Resource::inspect(const string& msg) const
{
  logger << "Inspecting resource " << getName() << ": ";
  if (!msg.empty()) logger  << msg;
  logger << endl;

  for (loadplanlist::const_iterator oo = getLoadPlans().begin();
    oo != getLoadPlans().end();
    ++oo)
  {
    logger << "  " << oo->getDate()
      << " qty:" << oo->getQuantity()
      << ", oh:" << oo->getOnhand();
    switch (oo->getEventType())
    {
    case 1:
      logger << ", " << oo->getOperationPlan() << endl;
      break;
    case 2:
      logger << ", set onhand to " << oo->getOnhand() << endl;
      break;
    case 3:
      logger << ", update minimum to " << oo->getMin() << endl;
      break;
    case 4:
      logger << ", update maximum to " << oo->getMax() << endl;
      break;
    case 5:
      logger << ", change setup to " << static_cast<const SetupEvent*>(&*oo)->getSetup();
      if (oo->getOperationPlan())
        logger << " on " << oo->getOperationPlan();
      logger << endl;
      break;
    }
  }
}


PyObject* Resource::inspectPython(PyObject* self, PyObject* args)
{
  try
  {
    // Pick up the resource
    Resource *res = nullptr;
    PythonData c(self);
    if (c.check(Resource::metadata))
      res = static_cast<Resource*>(self);
    else
      throw LogicException("Invalid resource type");

    // Parse the argument
    char *msg = nullptr;
    if (!PyArg_ParseTuple(args, "|s:inspect", &msg))
      return nullptr;
    
    res->inspect(msg ? msg : "");

    return Py_BuildValue("");
  }
  catch (...)
  {
    PythonType::evalException();
    return nullptr;
  }
}


void Resource::setMaximum(double m)
{
  if (m < 0)
    throw DataException("Maximum capacity for resource '" + getName() + "' must be postive");

  // There is already a maximum calendar.
  if (size_max_cal)
  {
    // We update the field, but don't use it yet.
    size_max = m;
    return;
  }

  // Mark as changed
  setChanged();

  // Set field
  size_max = m;

  // Create or update a single timeline max event
  for (loadplanlist::iterator oo=loadplans.begin(); oo!=loadplans.end(); oo++)
    if (oo->getEventType() == 4)
    {
      // Update existing event
      static_cast<loadplanlist::EventMaxQuantity *>(&*oo)->setMax(size_max);
      return;
    }
  // Create new event
  loadplanlist::EventMaxQuantity *newEvent =
    new loadplanlist::EventMaxQuantity(Date::infinitePast, &loadplans, size_max);
  loadplans.insert(newEvent);
}


void Resource::setMaximumCalendar(Calendar* c)
{
  // Resetting the same calendar
  if (size_max_cal == c) return;

  // Mark as changed
  setChanged();

  // Remove the current max events.
  for (loadplanlist::iterator oo=loadplans.begin(); oo!=loadplans.end(); )
    if (oo->getEventType() == 4)
    {
      loadplans.erase(&(*oo));
      delete &(*(oo++));
    }
    else ++oo;

  // Null pointer passed. Change back to time independent maximum size.
  if (!c)
  {
    setMaximum(size_max);
    return;
  }

  // Create timeline structures for every bucket.
  size_max_cal = c;
  double curMax = 0.0;
  for (CalendarDefault::EventIterator x(size_max_cal); x.getDate()<Date::infiniteFuture; ++x)
    if (curMax != x.getValue())
    {
      curMax = x.getValue();
      loadplanlist::EventMaxQuantity *newBucket =
        new loadplanlist::EventMaxQuantity(x.getDate(), &loadplans, curMax);
      loadplans.insert(newBucket);
    }
  size_max_cal->clearEventList();
}


void ResourceBuckets::setMaximumCalendar(Calendar* c)
{
  // Resetting the same calendar
  if (size_max_cal == c)
    return;

  // Mark as changed
  setChanged();

  // Remove the current set-onhand events.
  for (auto oo = loadplans.begin(); oo != loadplans.end(); )
  {
    loadplanlist::Event *tmp = &*oo;
    ++oo;
    if (tmp->getEventType() == 2)
    {
      loadplans.erase(tmp);
      delete tmp;
    }
  }

  // Create timeline structures for every bucket.
  size_max_cal = c;
  double v = 0.0;
  // Only create events in the time window from 3 years before current
  // till 6 years after the current date
  Date minEventDate = Plan::instance().getCurrent() - Duration(3L * 365L * 86400L);
  Date maxEventDate = Plan::instance().getCurrent() + Duration(6L * 365L * 86400L);
  for (CalendarDefault::EventIterator x(size_max_cal); x.getDate() < maxEventDate; ++x)
    if (v != x.getValue() && x.getDate() >= minEventDate)
    {
      v = x.getValue();
      loadplanlist::EventSetOnhand *newBucket =
        new loadplanlist::EventSetOnhand(x.getDate(), v);
      loadplans.insert(newBucket);
    }
  size_max_cal->clearEventList();
}


double ResourceBuckets::getMaxBucketCapacity() const
{
  double tmp = 0.0;
  for (auto oo = loadplans.begin(); oo != loadplans.end(); ++oo)
    if (oo->getEventType() == 2 && oo->getOnhand() > tmp)
      tmp = oo->getOnhand();
  return tmp;
}


void Resource::deleteOperationPlans(bool deleteLocked)
{
  // Delete the operationplans
  for (loadlist::iterator i=loads.begin(); i!=loads.end(); ++i)
    OperationPlan::deleteOperationPlans(i->getOperation(),deleteLocked);

  // Mark to recompute the problems
  setChanged();
}


Resource::~Resource()
{
  // Delete all operationplans
  // An alternative logic would be to delete only the loadplans for this
  // resource and leave the rest of the plan untouched. The currently
  // implemented method is way more drastic...
  deleteOperationPlans(true);

  // The Load and ResourceSkill objects are automatically deleted by the
  // destructor of the Association list class.

  // Delete setup event
  if (setup)
    delete setup;

  // Clean up references on the itemsupplier and itemdistribution models
  for (Item::iterator itm_iter = Item::begin(); itm_iter != Item::end(); ++itm_iter)
  {
    Item::supplierlist::const_iterator itmsup_iter = itm_iter->getSupplierIterator();
    while (ItemSupplier* itmsup = itmsup_iter.next())
      if (itmsup->getResource() == this)
        itmsup->setResource(nullptr);
    Item::distributionlist::const_iterator itmdist_iter = itm_iter->getDistributionIterator();
    while (ItemDistribution* itmdist = itmdist_iter.next())
      if (itmdist->getResource() == this)
        itmdist->setResource(nullptr);
  }
}


void Resource::setOwner(Resource* o)
{
  // Assure that all child resources are of the same type
  if (o)
  {
    auto firstchild = o->getFirstChild();
    if (firstchild)
    {
      bool parent_bucketized = firstchild->hasType<ResourceBuckets>();
      bool me_bucketized = hasType<ResourceBuckets>();
      if (parent_bucketized != me_bucketized)
        throw DataException("Aggregate resources can't mix bucketized resources with other types");
    }
  }
  HasHierarchy<Resource>::setOwner(o);
}


extern "C" PyObject* Resource::plan(PyObject *self, PyObject *args)
{
  // Get the resource model
  Resource* resource = static_cast<Resource*>(self);

  // Parse the Python arguments
  PyObject* buckets = nullptr;
  int ok = PyArg_ParseTuple(args, "O:plan", &buckets);
  if (!ok) return nullptr;

  // Validate that the argument supports iteration.
  PyObject* iter = PyObject_GetIter(buckets);
  if (!iter)
  {
    PyErr_Format(PyExc_AttributeError,"Argument to resource.plan() must support iteration");
    return nullptr;
  }

  // Return the iterator
  return new Resource::PlanIterator(resource, iter);
}


int Resource::PlanIterator::initialize()
{
  // Initialize the type
  PythonType& x = PythonExtension<Resource::PlanIterator>::getPythonType();
  x.setName("resourceplanIterator");
  x.setDoc("frePPLe iterator for resourceplan");
  x.supportiter();
  return x.typeReady();
}


Resource::PlanIterator::PlanIterator(Resource* r, PyObject* o) : bucketiterator(o)
{
  // Start date of the first bucket
  end_date = PyIter_Next(bucketiterator);
  if (!end_date)
  {
    logger << "Warning: No valid buckets for exporting resource plan on '" << r << "'" << endl;
    bucketiterator = nullptr;
    return;
  }

  // Collect all subresources
  if (!r)
  {
    bucketiterator = nullptr;
    throw LogicException("Creating resource plan iterator for nullptr resource");
  }
  else if (r->isGroup())
  {
    for (Resource::memberRecursiveIterator i(r); !i.empty(); ++i)
      if (!i->isGroup())
      {
        _res tmp;
        tmp.res = &*i;
        res_list.push_back(tmp);
      }
  }
  else
  {
    _res tmp;
    tmp.res = r;
    res_list.push_back(tmp);
  }

  // Initialize the iterator for all resources
  for (auto i = res_list.begin(); i != res_list.end(); ++i)
  {
    i->ldplaniter = Resource::loadplanlist::iterator(i->res->getLoadPlans().begin());
    i->bucketized = i->res->hasType<ResourceBuckets>();
    i->cur_date = PythonData(end_date).getDate();
    i->setup_loadplan = nullptr;
    i->prev_date = i->cur_date;
    i->cur_size = 0.0;
    i->cur_load = 0.0;

    if (i->bucketized)
    {
      // Scan forward to the first relevant bucket
      while (
        i->ldplaniter != i->res->getLoadPlans().end() 
        && (i->ldplaniter->getEventType() != 2 || i->ldplaniter->getDate() < i->cur_date)
        )
          ++(i->ldplaniter);
    }
    else
    {
      // Initialize unavailability iterators
      i->prev_value = true;
      if (i->res->getLocation() && i->res->getLocation()->getAvailable())
      {
        i->unavailLocIter = Calendar::EventIterator(i->res->getLocation()->getAvailable(), i->cur_date);
        i->prev_value = (i->unavailLocIter.getCalendar()->getValue(i->cur_date) != 0);
      }
      if (i->res->getAvailable())
      {
        i->unavailIter = Calendar::EventIterator(i->res->getAvailable(), i->cur_date);
        if (i->prev_value)
          i->prev_value = (i->unavailIter.getCalendar()->getValue(i->cur_date) != 0);
      }

      // Advance loadplan iterator just beyond the starting date
      while (i->ldplaniter != i->res->getLoadPlans().end() && i->ldplaniter->getDate() <= i->cur_date)
      {
        unsigned short tp = i->ldplaniter->getEventType();
        if (tp == 4)
          // New max size
          i->cur_size = i->ldplaniter->getMax();
        else if (tp == 1)
        {
          const LoadPlan* ldplan = dynamic_cast<const LoadPlan*>(&*(i->ldplaniter));
          if (
            ldplan->getOperationPlan()->getSetupEnd() != ldplan->getOperationPlan()->getStart()
            && ldplan->getQuantity() > 0
            )
            i->setup_loadplan = ldplan;
          else
            i->setup_loadplan = nullptr;
          i->cur_load = ldplan->getOnhand();
        }
        ++(i->ldplaniter);
      }
    }
  }
}


Resource::PlanIterator::~PlanIterator()
{
  if (bucketiterator)
    Py_DECREF(bucketiterator);
  if (start_date)
    Py_DECREF(start_date);
  if (end_date)
    Py_DECREF(end_date);
}


void Resource::PlanIterator::update(Resource::PlanIterator::_res* i, Date till)
{
  long timedelta;
  if (i->unavailIter.getCalendar() || i->unavailLocIter.getCalendar())
  {
    // Advance till the iterator exceeds the target date
    while (
      (i->unavailLocIter.getCalendar() && i->unavailLocIter.getDate() <= till)
      || (i->unavailIter.getCalendar() && i->unavailIter.getDate() <= till)
      )
    {
      if (i->unavailIter.getCalendar() &&
        (!i->unavailLocIter.getCalendar() || i->unavailIter.getDate() < i->unavailLocIter.getDate()))
      {
        timedelta = i->unavailIter.getDate() - i->prev_date;
        i->prev_date = i->unavailIter.getDate();
      }
      else
      {
        timedelta = i->unavailLocIter.getDate() - i->prev_date;
        i->prev_date = i->unavailLocIter.getDate();
      }
      if (i->prev_value)
      {
        bucket_available += i->cur_size * timedelta / 3600;
        bucket_load += i->cur_load * timedelta / 3600;
      }
      else
        bucket_unavailable += i->cur_size * timedelta / 3600;
      if (i->unavailIter.getCalendar() && i->unavailIter.getDate() == i->prev_date)
      {
        // Increment only resource unavailability iterator        
        ++(i->unavailIter);
        if (i->unavailLocIter.getCalendar() && i->unavailLocIter.getDate() == i->prev_date)
          // Increment both resource and location unavailability iterators
          ++(i->unavailLocIter);
      }
      else if (i->unavailLocIter.getCalendar() && i->unavailLocIter.getDate() == i->prev_date)
        // Increment only location unavailability iterator
        ++(i->unavailLocIter);
      else
        throw LogicException("Unreachable code");
      i->prev_value = true;
      if (i->unavailIter.getCalendar())
        i->prev_value = (i->unavailIter.getCalendar()->getValue(i->prev_date) != 0);
      if (i->unavailLocIter.getCalendar() && i->prev_value)
        i->prev_value = (i->unavailLocIter.getCalendar()->getValue(i->prev_date) != 0);
    }
    // Account for time period finishing at the "till" date
    timedelta = till - i->prev_date;
    if (i->prev_value)
    {
      bucket_available += i->cur_size * timedelta / 3600;
      bucket_load += i->cur_load * timedelta / 3600;
    }
    else
      bucket_unavailable += i->cur_size * timedelta / 3600;
  }
  else
  {
    // All time is available on this resource
    timedelta = till - i->prev_date;
    bucket_available += i->cur_size * timedelta / 3600;
    bucket_load += i->cur_load  * timedelta / 3600;
  }
  // Remember till which date we already have reported
  i->prev_date = till;
}


PyObject* Resource::PlanIterator::iternext()
{
  if (!bucketiterator)
    return nullptr;

  // Reset counters
  bucket_available = 0.0;
  bucket_unavailable = 0.0;
  bucket_load = 0.0;
  bucket_setup = 0.0;
  if (start_date)
    Py_DECREF(start_date);

  // Repeat until a non-empty bucket is found
  do
  {
    // Get the start and end date of the current bucket
    start_date = end_date;
    end_date = PyIter_Next(bucketiterator);
    if (!end_date)
      return nullptr;
    Date cpp_start_date = PythonData(start_date).getDate();
    Date cpp_end_date = PythonData(end_date).getDate();

    // Find the load of all resources in this bucket
    for (auto i = res_list.begin(); i != res_list.end(); ++i)
    {
      i->cur_date = cpp_end_date;
      if (i->bucketized)
      {
        // Bucketized resource
        while (
          i->ldplaniter != i->res->getLoadPlans().end()
          && i->ldplaniter->getDate() < cpp_end_date
          )
        {
          // At this point ldplaniter points to a bucket start event in the
          // current reporting bucket
          if (i->res->isTime())
            bucket_available += i->ldplaniter->getOnhand() / 3600;
          else
            bucket_available += i->ldplaniter->getOnhand();

          // Advance the loadplan iterator to the start of the next bucket
          ++(i->ldplaniter);
          while (
            i->ldplaniter != i->res->getLoadPlans().end()
            && i->ldplaniter->getEventType() != 2
            )
          {
            if (i->ldplaniter->getEventType() == 1)
            {
              if (i->res->isTime())
                bucket_load -= i->ldplaniter->getQuantity() / 3600;
              else
                bucket_load -= i->ldplaniter->getQuantity();
            }
            ++(i->ldplaniter);
          }
        }
      }
      else
      {
        // Default resource

        // Measure from beginning of the bucket till the first event in this bucket
        if (i->ldplaniter != i->res->getLoadPlans().end() && i->ldplaniter->getDate() < i->cur_date)
          update(&*i, i->ldplaniter->getDate());

        // Advance the loadplan iterator to the next event date
        while (i->ldplaniter != i->res->getLoadPlans().end() && i->ldplaniter->getDate() <= i->cur_date)
        {
          // Measure from the previous event till the current one
          update(&*i, i->ldplaniter->getDate());

          // Process the event
          unsigned short tp = i->ldplaniter->getEventType();
          if (tp == 4)
            // New max size
            i->cur_size = i->ldplaniter->getMax();
          else if (tp == 1)
          {
            const LoadPlan* ldplan = dynamic_cast<const LoadPlan*>(&*(i->ldplaniter));
            assert(ldplan);
            if (
              ldplan->getOperationPlan()->getSetupEnd() != ldplan->getOperationPlan()->getStart()
              && ldplan->getQuantity() > 0
              )
              i->setup_loadplan = ldplan;
            else
              i->setup_loadplan = nullptr;
            i->cur_load = ldplan->getOnhand();
          }

          // Move to the next event
          ++(i->ldplaniter);
        }

        // Measure from the previous event till the end of the bucket
        update(&*i, i->cur_date);
      }

      // Measure setup
      if (i->res->getSetupMatrix() && !i->bucketized)
      {
        DateRange bckt(cpp_start_date, cpp_end_date);
        for (auto j = i->res->getLoadPlans().begin(); j != i->res->getLoadPlans().end(); ++j)
        {
          auto tmp = j->getOperationPlan();
          if (tmp && j->getQuantity() < 0)
          {
            auto stp = DateRange(tmp->getStart(), tmp->getSetupEnd());
            bucket_setup -= static_cast<long>(bckt.overlap(stp)) * j->getQuantity();
          }
        }
      }
    }
  } 
  while (!bucket_available && !bucket_unavailable && !bucket_load && !bucket_setup);

  // Return the result
  bucket_setup /= 3600.0;
  bucket_load -= bucket_setup;
  return Py_BuildValue(
    "{s:O,s:O,s:d,s:d,s:d,s:d,s:d}",
    "start", start_date,
    "end", end_date,
    "available", bucket_available,
    "load", bucket_load,
    "unavailable", bucket_unavailable,
    "setup", bucket_setup,
    "free", bucket_available - bucket_load - bucket_setup
    );
}


bool Resource::hasSkill(Skill* s, Date st, Date nd, ResourceSkill** resSkill) const
{
  if (!s)
  {
    if (resSkill)
      *resSkill = nullptr;
    return false;
  }

  Resource::skilllist::const_iterator i = getSkills();
  while (ResourceSkill *rs = i.next())
  {
    if (rs->getSkill() == s
      && st >= rs->getEffective().getStart()
      && nd <= rs->getEffective().getEnd())
    {
      if (resSkill)
        *resSkill = rs;
      return true;
    }
  }
  if (resSkill)
    *resSkill = nullptr;
  return false;
}


void Resource::setSetupMatrix(SetupMatrix *s)
{
  if (hasType<ResourceBuckets>())
    throw DataException("No setup calendar can be defined on bucketized resources");
  setupmatrix = s;
}


SetupEvent* Resource::getSetupAt(Date d, OperationPlan* opplan)
{
  LoadPlan* ldplan = nullptr;
  if (opplan)
  {
    for (auto l = opplan->getLoadPlans(); l != opplan->endLoadPlans(); ++l)
      if (l->getResource() == this && l->getQuantity() < 0.0)
      {
        ldplan = &*l;
        break;
      }
  }
  auto tmp = ldplan ? getLoadPlans().begin(ldplan) : getLoadPlans().rbegin();
  while (tmp != getLoadPlans().end())
  {
    if (tmp->getEventType() == 5 && (!opplan || opplan != tmp->getOperationPlan()) && (
      tmp->getDate() < d ||
      (tmp->getDate() == d && opplan && tmp->getOperationPlan() && *opplan < *tmp->getOperationPlan())
      ))
      return const_cast<SetupEvent*>(static_cast<const SetupEvent*>(&*tmp));
    --tmp;
  }
  return nullptr;
}


void Resource::updateSetupTime() const
{
  bool tmp = OperationPlan::setPropagateSetups(false);
  if (setupmatrix)
  {
    bool changed;
    do
    {
      changed = false;
      for (auto qq = getLoadPlans().rbegin(); qq != getLoadPlans().end() && !changed; --qq)
        if (qq->getEventType() == 1 && qq->getQuantity() < 0.0 && !qq->getOperationPlan()->getConfirmed())
          changed = qq->getOperationPlan()->updateSetupTime();
    }
    while (changed);
  }
  OperationPlan::setPropagateSetups(tmp);
}


extern "C" PyObject* ResourceBuckets::computeBucketAvailability(PyObject *self, PyObject *args)
{
  // Get the resource model
  ResourceBuckets* res = static_cast<ResourceBuckets*>(self);

  // Parse the Python arguments
  PyObject* pycal = nullptr;
  int debug = false;
  int ok = PyArg_ParseTuple(args, "O|p:computeAvailability", &pycal, &debug);
  if (!ok)
    return nullptr;
  if (!PyObject_TypeCheck(pycal, CalendarDefault::metadata->pythonClass))
  {
    PyErr_SetString(PythonDataException, "argument must be of type calendar");
    return nullptr;
  }
  Calendar* cal = static_cast<Calendar*>(pycal);

  // Mark as changed
  res->setChanged();

  // Remove the current set-onhand events.
  for (auto oo = res->getLoadPlans().begin(); oo != res->getLoadPlans().end(); )
  {
    loadplanlist::Event *tmp = &*oo;
    ++oo;
    if (tmp->getEventType() == 2)
    {
      res->getLoadPlans().erase(tmp);
      delete tmp;
    }
  }

  // Create timeline structures for every bucket.
  if (debug)
  {
    logger << "Computing availability for resource '" << res << "' with buckets from calendar '" << cal << "'" << endl;
    logger << "   Size calendar: " << res->getMaximumCalendar() << endl;
    logger << "   Availability calendar: " << res->getAvailable() << endl;
    logger << "   Location availability calendar: " << (res->getLocation() ? res->getLocation()->getAvailable() : nullptr) << endl;
  }
  CalendarDefault::EventIterator res_max(res->getMaximumCalendar());
  CalendarDefault::EventIterator avail_res(res->getAvailable());
  CalendarDefault::EventIterator avail_loc(res->getLocation() ? res->getLocation()->getAvailable() : nullptr);
  Date bucketstart;
  double cur_size = res->getMaximumCalendar() ? res->getMaximumCalendar()->getDefault() : res->getMaximum();
  bool cur_available = true;
  // Only create events in the time window from 3 years before current
  // till 6 years after the current date
  Date minEventDate = Plan::instance().getCurrent() - Duration(3L * 365L * 86400L);
  Date maxEventDate = Plan::instance().getCurrent() + Duration(6L * 365L * 86400L);
  for (CalendarDefault::EventIterator bckt(cal); bckt.getDate() < maxEventDate; ++bckt)
  {
    // Advance availability and max calendars till we hit the end of the bucket
    double available = 0.0;
    Date prev_evt = bucketstart;
    do
    {
      // Find the next event date
      Date evt = bckt.getDate();
      if (avail_res.getDate() < evt)
        evt = avail_res.getDate();
      if (avail_loc.getDate() < evt)
        evt = avail_loc.getDate();
      if (res_max.getDate() < evt)
        evt = res_max.getDate();

      // Add availability between the previous and current event
      if (cur_available && cur_size > 0.0)
        available += cur_size * (evt - prev_evt).getSeconds();

      // Update availability and size at the event date
      cur_available = true;
      if (res->getAvailable())
      {
        if (avail_res.getDate() == evt && avail_res.getValue() == 0)
          cur_available = false;
        else if (res->getAvailable() && avail_res.getDate() != evt && avail_res.getPrevValue() == 0)
          cur_available = false;
      }
      if (cur_available && res->getLocation() && res->getLocation()->getAvailable())
      {
        if (avail_loc.getDate() == evt && avail_loc.getValue() == 0)
          cur_available = false;
        else if (avail_loc.getDate() != evt && avail_loc.getPrevValue() == 0)
          cur_available = false;
      }
      if (res->getMaximumCalendar() && res_max.getDate() == evt)
        cur_size = res_max.getValue();

      // Advance to the next event
      if (avail_res.getDate() == evt)
        ++avail_res;
      if (avail_loc.getDate() == evt)
        ++avail_loc;
      if (res_max.getDate() == evt)
        ++res_max;
      prev_evt = evt;
    } 
    while (avail_res.getDate() <= bckt.getDate() || avail_loc.getDate() <= bckt.getDate() || res_max.getDate() <= bckt.getDate());
    if (bckt.getDate() > prev_evt && cur_available && cur_size > 0.0)
      available += cur_size * (bckt.getDate() - prev_evt).getSeconds();

    // Create an event for this bucket in the timeline
    if (bucketstart > minEventDate)
    {
      loadplanlist::EventSetOnhand *newBucket =
        new loadplanlist::EventSetOnhand(bucketstart, available);
      res->getLoadPlans().insert(newBucket);
      if (debug)
        logger << "   => Bucket from " << bucketstart << " till " << bckt.getDate() << ": " << available << endl;
    }

    // Remember the bucket start
    bucketstart = bckt.getDate();
  }
  cal->clearEventList();

  // Set a flag that this resource's calendar represents machine-time from now onwards
  res->computedFromCalendars = true;

  // None return value
  return Py_BuildValue("");
}

}
